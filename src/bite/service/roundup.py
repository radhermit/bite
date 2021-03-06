"""XML-RPC access to Roundup.

API docs:
    http://www.roundup-tracker.org/docs/xmlrpc.html
    http://roundup.sourceforge.net/docs/user_guide.html#query-tracker
"""

from base64 import b64encode
from itertools import chain, islice
import re

from datetime import datetime
from snakeoil.klass import aliased, alias

from ._reqs import NullRequest, ParseRequest, req_cmd, BaseCommentsRequest
from ._rpc import Multicall, RPCRequest
from ._xmlrpc import Xmlrpc
from ..cache import Cache, csv2tuple
from ..exceptions import RequestError, BiteError
from ..objects import Item, Attachment, Comment
from ..utc import utc


def parsetime(time):
    """Parse custom date format that roundup uses."""
    date = datetime.strptime(time, '<Date %Y-%m-%d.%X.%f>')
    # strip microseconds and assume UTC
    return date.replace(microsecond=0).astimezone(utc)


class RoundupError(RequestError):

    def __init__(self, msg, code=None, text=None):
        # extract roundup error code and msg if it exists
        roundup_exc = re.match(r"^<\w+ '(.+)'>:(.+)$", msg)
        if roundup_exc:
            code, msg = roundup_exc.groups()
        msg = 'Roundup error: ' + msg
        super().__init__(msg, code, text)


class RoundupIssue(Item):

    # assumes bugs.python.org issue schema
    attributes = {
        # from schema list
        'assignee': 'Assignee',
        'components': 'Components',
        'dependencies': 'Depends',
        'files': 'Attachments',
        'keywords': 'Keywords',
        # 'message_count': 'Comment count',
        'messages': 'Comments',
        'nosy': 'Nosy List',
        # 'nosy_count': 'Nosy count',
        'priority': 'Priority',
        'pull_requests': 'PRs',
        'resolution': 'Resolution',
        'severity': 'Severity',
        'stage': 'Stage',
        'status': 'Status',
        'superseder': 'Duplicate of',
        'title': 'Title',
        'type': 'Type',
        'versions': 'Versions',

        # properties not listed by schema output, but included by default
        'id': 'ID',
        'creator': 'Reporter',
        'creation': 'Created',
        'actor': 'Modified by',
        'activity': 'Modified',
    }

    attribute_aliases = {
        'owner': 'assignee',
        'created': 'creation',
        'modified': 'activity',
    }

    _print_fields = (
        ('title', 'Title'),
        ('assignee', 'Assignee'),
        ('creation', 'Created'),
        ('creator', 'Reporter'),
        ('activity', 'Modified'),
        ('actor', 'Modified by'),
        ('id', 'ID'),
        ('status', 'Status'),
        ('dependencies', 'Depends'),
        ('resolution', 'Resolution'),
        ('priority', 'Priority'),
        ('superseder', 'Duplicate'),
        ('keywords', 'Keywords'),
    )

    type = 'issue'

    def __init__(self, service, **kw):
        self.service = service
        for k, v in kw.items():
            if k in ('creation', 'activity'):
                setattr(self, k, parsetime(v))
            elif k in ('creator', 'actor'):
                try:
                    username = self.service.cache['users'][int(v)-1]
                except IndexError:
                    # cache needs update
                    username = v
                setattr(self, k, username)
            elif k == 'status':
                try:
                    status = self.service.cache['status'][int(v)-1]
                except IndexError:
                    # cache needs update
                    status = v
                setattr(self, k, status)
            elif k == 'priority' and v is not None:
                try:
                    priority = self.service.cache['priority'][int(v)-1]
                except IndexError:
                    # cache needs update
                    priority = v
                setattr(self, k, priority)
            elif k == 'keyword' and v is not None:
                keywords = []
                for keyword in v:
                    try:
                        keywords.append(self.service.cache['keyword'][int(keyword)-1])
                    except IndexError:
                        # cache needs update
                        keywords.append(keyword)
                setattr(self, k, keywords)
            else:
                setattr(self, k, v)


class RoundupComment(Comment):
    pass


class RoundupAttachment(Attachment):
    pass


class RoundupCache(Cache):

    def __init__(self, **kw):
        # default to empty values
        defaults = {
            'status': (),
            'priority': (),
            'keyword': (),
            'users': (),
        }

        converters = {
            'status': csv2tuple,
            'priority': csv2tuple,
            'keyword': csv2tuple,
            'users': csv2tuple,
        }

        super().__init__(defaults=defaults, converters=converters, **kw)


class Roundup(Xmlrpc):
    """Service supporting the Roundup issue tracker."""

    _service = 'roundup'
    _service_error_cls = RoundupError
    _cache_cls = RoundupCache

    item = RoundupIssue
    item_endpoint = '/issue{id}'
    attachment = RoundupAttachment
    attachment_endpoint = '/file{id}'

    def __init__(self, **kw):
        super().__init__(endpoint='/xmlrpc', **kw)
        # bugs.python.org requires this header
        self.session.headers.update({
            'X-Requested-With': 'XMLHttpRequest'
        })

    @property
    def cache_updates(self):
        """Pull latest data from service for cache update."""
        config_updates = {}
        values = {}

        # login required to grab user data
        self.client.login(force=True)

        attrs = ('status', 'priority', 'keyword', 'user')
        reqs = []
        # pull list of specified attribute types
        names = list(self.multicall(command='list', params=attrs).send())

        # The list command doesn't return the related values in the order that
        # values their underlying IDs so we have to roll lookups across the
        # entire scope to determine them.
        for i, attr in enumerate(attrs):
            data = names[i]
            values[attr] = data
            params = ([attr, x] for x in data)
            reqs.append(self.multicall(command='lookup', params=params))

        data = self.merged_multicall(reqs=reqs).send()
        for attr in ('status', 'priority', 'keyword', 'user'):
            order = next(data)
            values[attr] = [x for order, x in sorted(zip(order, values[attr]))]

        # don't sort, ordering is important for the mapping to work properly
        config_updates['status'] = tuple(values['status'])
        config_updates['priority'] = tuple(values['priority'])
        config_updates['keyword'] = tuple(values['keyword'])
        if 'user' in values:
            config_updates['users'] = tuple(values['user'])

        return config_updates

    def inject_auth(self, request, params):
        self.session.headers['Authorization'] = str(self.auth)
        self.authenticated = True
        return request, params

    def _get_auth_token(self, user, password, **kw):
        """Get an authentication token from the service."""
        # generate HTTP basic auth token
        if isinstance(user, str):
            user = user.encode('latin1')
        if isinstance(password, str):
            password = password.encode('latin1')
        authstr = 'Basic ' + (b64encode(b':'.join((user, password))).strip()).decode()
        return authstr


@req_cmd(Roundup, cmd='search')
class _SearchRequest(ParseRequest, RPCRequest):
    """Construct a search request."""

    # map from standardized kwargs name to expected service parameter name
    _params_map = {
        'created': 'creation',
        'modified': 'activity',
    }

    def __init__(self, fields=None, **kw):
        super().__init__(command='filter', **kw)

        # limit fields by default to decrease requested data size and speed up response
        if fields is None:
            fields = ['id', 'assignee', 'title']
        else:
            unknown_fields = set(fields).difference(self.service.item.attributes.keys())
            if unknown_fields:
                raise BiteError(f"unknown fields: {', '.join(unknown_fields)}")
            self.options.append(f"Fields: {' '.join(fields)}")
        self.fields = fields

    def parse(self, data):
        # Roundup search requests return a list of matching IDs that we resubmit
        # via a multicall to grab ticket data if any matches exist.
        if data:
            issues = self.service.GetItemRequest(ids=data, fields=self.fields).send()
            yield from issues

    def encode_params(self):
        params = self.params.copy()
        sort = params.pop('sort')
        params = ('issue', None, params, sort)
        return super().encode_params(params)

    @aliased
    class ParamParser(ParseRequest.ParamParser):

        # map of allowed sorting input values to service parameters
        _sorting_map = {
            'assignee': 'assignee',
            'id': 'id',
            'creator': 'creator',
            'created': 'creation',
            'modified': 'activity',
            'modified-by': 'actor',
            'components': 'components',
            'depends': 'dependencies',
            'keywords': 'keywords',
            'comments': 'message_count',
            'cc': 'nosy_count',
            'priority': 'priority',
            'prs': 'pull_requests',
            'resolution': 'resolution',
            'severity': 'severity',
            'stage': 'stage',
            'status': 'status',
            'title': 'title',
            'type': 'type',
        }

        def _finalize(self, **kw):
            if not self.params or self.params.keys() == {'sort'}:
                raise BiteError('no supported search terms or options specified')

            # default to sorting ascending by ID
            self.params.setdefault('sort', [('+', 'id')])

            # default to showing issues that aren't closed
            # TODO: use service cache with status names here
            if 'status' not in self.params:
                cached_statuses = self.service.cache['status']
                if cached_statuses:
                    open_statuses = list(
                        i + 1 for i, x in enumerate(cached_statuses) if x != 'closed')
                    self.params['status'] = open_statuses

        def terms(self, k, v):
            self.params['title'] = v
            self.options.append(f"Summary: {', '.join(v)}")

        @alias('modified')
        def created(self, k, v):
            self.params[k] = f"{v.strftime('%Y-%m-%d.%H:%M:%S')};."
            self.options.append(f'{k.capitalize()}: {v} (since {v.isoformat()})')

        def sort(self, k, v):
            sorting_terms = []
            for sort in v:
                if sort[0] == '-':
                    key = sort[1:]
                    order = '-'
                else:
                    key = sort
                    order = '+'
                try:
                    order_var = self._sorting_map[key]
                except KeyError:
                    choices = ', '.join(sorted(self._sorting_map.keys()))
                    raise BiteError(
                        f'unable to sort by: {key!r} (available choices: {choices}')
                sorting_terms.append((order, order_var))
            self.params[k] = sorting_terms
            self.options.append(f"Sort order: {', '.join(v)}")


@req_cmd(Roundup)
class _GetItemRequest(Multicall):
    """Construct an item request."""

    def __init__(self, *, ids, fields=None, **kw):
        super().__init__(command='display', **kw)
        if ids is None:
            raise ValueError(f'No {self.service.item.type} ID(s) specified')

        # Request all fields by default, roundup says it does this already when
        # no fields are specified, but it still doesn't return all fields.
        if fields is None:
            fields = self.service.item.attributes.keys()

        self.params = (chain([f'issue{i}'], fields) for i in ids)
        self.ids = ids

    def parse(self, data):
        # unwrap multicall result
        issues = super().parse(data)
        for i, issue in enumerate(issues):
            yield self.service.item(self.service, **issue)


@req_cmd(Roundup, cmd='get')
class _GetRequest(_GetItemRequest):
    """Construct a get request."""

    def __init__(self, get_comments=True, get_attachments=True, **kw):
        super().__init__(**kw)
        self._get_comments = get_comments
        self._get_attachments = get_attachments

    def handle_exception(self, e):
        if e.code == 'exceptions.IndexError':
            # issue doesn't exist
            raise RoundupError(msg=e.msg)
        elif e.code == 'exceptions.KeyError':
            # field doesn't exist
            raise RoundupError(msg="field doesn't exist: {}".format(e.msg))
        raise

    def parse(self, data):
        issues = list(super().parse(data))
        reqs = []

        for issue in issues:
            if issue.files and self._get_attachments:
                reqs.append(
                    self.service.AttachmentsRequest(attachment_ids=issue.files))
            else:
                reqs.append(NullRequest())

            if issue.messages and self._get_comments:
                reqs.append(
                    self.service.CommentsRequest(comment_ids=issue.messages))
            else:
                reqs.append(NullRequest())

        issue_data = self.service.merged_multicall(reqs=reqs).send()
        # TODO: There doesn't appear to be a way to request issue changes via the API.
        # changes = self.service.ChangesRequest(ids=self.ids).send()

        for issue in issues:
            attachments = next(issue_data)
            comments = next(issue_data)
            issue.attachments = next(attachments)
            issue.comments = next(comments)
            issue.changes = ()
            yield issue


@req_cmd(Roundup, cmd='attachments')
class _AttachmentsRequest(Multicall):
    """Construct an attachments request."""

    def __init__(self, ids=None, attachment_ids=None, get_data=False, **kw):
        # TODO: add support for specifying issue IDs
        if attachment_ids is None:
            raise ValueError('No attachment ID(s) specified')
        super().__init__(command='display', **kw)

        fields = ['name', 'type', 'creator', 'creation']
        if get_data:
            fields.append('content')

        self.params = (chain([f'file{i}'], fields) for i in attachment_ids)
        self.ids = ids
        self.attachment_ids = attachment_ids

    def parse(self, data):
        # unwrap multicall result
        data = super().parse(data)

        if self.attachment_ids:
            ids = self.attachment_ids
        else:
            ids = self.ids

        yield tuple(RoundupAttachment(
            id=ids[i], filename=d['name'], data=d.get('content'),
            creator=d['creator'], created=parsetime(d['creation']), mimetype=d['type'])
            for i, d in enumerate(data))


@req_cmd(Roundup, cmd='comments')
class _CommentsRequest(BaseCommentsRequest, Multicall):
    """Construct a comments request."""

    def __init__(self, comment_ids=None, fields=(), **kw):
        super().__init__(command='display', **kw)

        if not any((self.ids, comment_ids)):
            raise ValueError('No ID(s) specified')
        if self.ids:
            self.options.append(f"IDs: {', '.join(self.ids)}")

        self.fields = fields
        self.comment_ids = comment_ids

    def encode_params(self):
        # get message IDs for given issue IDs
        if self.ids:
            id_info = []
            self.comment_ids = []
            req_fields = ('id', 'messages')
            issues = self.service.GetItemRequest(ids=self.ids, fields=req_fields).send()
            for i, x in enumerate(issues):
                id_info.append((self.ids[i], len(x.messages)))
                self.comment_ids.extend(x.messages)
            self._id_info = tuple(id_info)

        params = (chain([f'msg{i}'], self.fields) for i in self.comment_ids)
        return super().encode_params(params)

    def parse(self, data):
        # unwrap multicall result
        data = super().parse(data)
        def items():
            if self.ids:
                count = 0
                for _id, length in self._id_info:
                    l = []
                    for i, d in enumerate(islice(data, length)):
                        l.append(RoundupComment(
                            id=self.comment_ids[count], count=i, text=d['content'].strip(),
                            created=parsetime(d['date']), creator=d['author']))
                        count += 1
                    yield tuple(l)
            else:
                yield tuple(RoundupComment(
                    id=self.comment_ids[i], count=i, text=d['content'].strip(),
                    created=parsetime(d['date']), creator=d['author'])
                    for i, d in enumerate(data))
        yield from self.filter(items())


@req_cmd(Roundup, cmd='schema')
class _SchemaRequest(RPCRequest):
    """Construct a schema request."""

    def __init__(self, **kw):
        super().__init__(command='schema', **kw)
