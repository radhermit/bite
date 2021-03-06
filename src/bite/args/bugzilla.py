import argparse
from functools import partial

from .. import args
from ..argparser import ParseStdin
from ..objects import TimeInterval
from ..utils import str2bool


class ChangedTimeTuple(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        field, value = values
        setattr(namespace, self.dest, (field, TimeInterval(value)))


class Bugzilla4_4Opts(args.ServiceOpts):
    """Bugzilla 4.4 options."""

    _service = 'bugzilla4.4'

    _config_map = args.ServiceOpts._config_map.copy()
    _config_map['restrict_login'] = str2bool

    def add_main_opts(self, service):
        """Add service specific arguments."""
        from ..scripts.bite import auth_opts
        auth_opts.add_argument(
            '--restrict', action='store_true', dest='restrict_login',
            help='restrict the login to your IP address')


class Bugzilla5_0Opts(Bugzilla4_4Opts):
    """Bugzilla 5.0 options."""

    _service = 'bugzilla5.0'


class Bugzilla5_2Opts(Bugzilla5_0Opts):
    """Bugzilla 5.2 options."""

    _service = 'bugzilla5.2'


class Attach(args.Attach, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # positional args
        self.parser.add_argument(
            'filepath', type=str,
            help='path of the file to attach')
        self.parser.add_argument(
            'ids', type='ids', nargs='+', metavar='ID', action='parse_stdin',
            help='bug ID(s) where the file should be attached')

        # optional args
        self.opts.add_argument(
            '-c', '--content-type',
            help='mimetype of the file e.g. text/plain (default: auto-detect)')
        self.opts.add_argument(
            '-p', '--patch', action='store_true', dest='is_patch',
            help='attachment is a patch')


class Attachments(args.Attachments, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # optional args
        self.opts.add_argument(
            '-l', '--list', action='store_true', dest='show_metadata',
            help='list attachment metadata')


class Create(args.Create, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # optional args
        person = self.parser.add_argument_group('Person related')
        person.add_argument(
            '-a', '--assigned-to',
            help='assign bug to someone other than the default assignee')
        person.add_argument(
            '--qa-contact',
            help='set the QA Contact for this bug')
        person.add_argument(
            '--cc', type='str_list',
            help='add a list of emails to CC list')
        attr = self.parser.add_argument_group('Attribute related')
        attr.add_argument(
            '-d', '--description',
            help='description of the bug')
        attr.add_argument(
            '-S', '--severity',
            help='set the severity for the new bug')
        attr.add_argument(
            '-s', '--status',
            help='set the status for the new bug')
        attr.add_argument(
            '-t', '--title', dest='summary',
            help='title of bug')
        attr.add_argument(
            '-u', '--url',
            help='URL for this bug')
        attr.add_argument(
            '--product',
            help='product')
        attr.add_argument(
            '-C', '--component',
            help='component')
        attr.add_argument(
            '--version',
            help='version of the product')
        attr.add_argument(
            '--os', dest='op_sys', metavar='OS',
            help='operating system for this bug')
        attr.add_argument(
            '--platform',
            help='platform for this bug')
        attr.add_argument(
            '--priority',
            help='set priority for the new bug')
        attr.add_argument(
            '--target-milestone',
            help='set a target milestone for this bug')
        attr.add_argument(
            '--alias',
            help='set the alias for this bug')
        attr.add_argument(
            '--groups', type='str_list',
            help='list of groups this bug should be put into')
        attr.add_argument(
            '--blocks', type='id_list',
            help='list of bugs this bug blocks')
        attr.add_argument(
            '--depends', type='id_list',
            help='list of bugs this bug depends on')
        attr.add_argument(
            '-K', '--keywords', type='str_list',
            help='set the keywords of this bug')


class Get(args.Get, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args(history=True)
        # optional args
        self.opts.add_argument(
            '-O', '--show-obsolete', action='store_true',
            help='show obsolete attachments')


class Modify(args.Modify, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # optional args
        self.attr.add_argument(
            '-S', '--severity',
            help='set severity for this bug')
        self.attr.add_argument(
            '-t', '--title', dest='summary',
            help='set title of bug')
        self.attr.add_argument(
            '-u', '--url',
            help='set URL field of bug')
        self.attr.add_argument(
            '-V', '--version',
            help='set the version for this bug'),
        self.attr.add_argument(
            '-W', '--whiteboard',
            help='set status whiteboard'),
        self.attr.add_argument(
            '--alias', action='csv_elements',
            help='add/remove/set aliases',
            docs="""
                Add, remove, or set bug aliases.

                Use comma-separated values to add, remove, or set aliases for a
                given bug. Use the prefixes '+' and '-' for each value to add
                and remove aliases, respectively. In order to set aliases for a
                bug, don't use any prefixes for the passed values.

                Note that setting aliases overrides the current aliases for the
                bug as well as any passed add/remove values.

                In addition, this action can only be performed on a single bug
                at a time so passing multiple bug ID targets will cause an
                error.
            """)
        self.attr.add_argument(
            '--blocks', action='csv_elements', metavar='BUG_ID',
            help='add/remove/set blockers',
            docs="""
                Add, remove, or set bug blockers.

                Use comma-separated bug IDS to add, remove, or set blockers for a
                given bug. Use the prefixes '+' and '-' for each ID to add
                and remove blockers, respectively. In order to set blockers for a
                bug, don't use any prefixes for the passed IDs.

                Note that setting blockers overrides the current blockers for the
                bug as well as any passed add/remove values.
            """)
        self.attr.add_argument(
            '--component',
            help='change the component for this bug')
        self.attr.add_argument(
            '--depends', action='csv_elements', metavar='BUG_ID',
            help='add/remove/set dependencies',
            docs="""
                Add, remove, or set bug dependencies.

                Use comma-separated bug IDS to add, remove, or set dependencies
                for a given bug. Use the prefixes '+' and '-' for each ID to
                add and remove dependencies, respectively. In order to set
                dependencies for a bug, don't use any prefixes for the passed
                IDs.

                Note that setting dependencies overrides the current
                dependencies for the bug as well as any passed add/remove
                values.
            """)
        self.attr.add_argument(
            '--groups', action='csv_negations', metavar='GROUP',
            help='add/remove groups',
            docs="""
                Add or remove bug groups.

                Use comma-separated values to add or remove groups for a given
                bug. Use the prefixes '+' and '-' for each ID to add and remove
                groups, respectively.
            """)
        self.attr.add_argument(
            '-K', '--keywords', action='csv_elements', metavar='KEYWORDS',
            help='add/remove/set keywords',
            docs="""
                Add, remove, or set bug keywords.

                Use comma-separated values to add, remove, or set keywords for
                a given bug. Use the prefixes '+' and '-' for each value to add
                and remove keywords, respectively. In order to set keywords for
                a bug, don't use any prefixes for the passed values.

                Note that setting keywords overrides the current keywords for
                the bug as well as any passed add/remove values.
            """)
        self.attr.add_argument(
            '--target-milestone',
            help='set a target milestone for this bug')
        self.attr.add_argument(
            '--os', dest='op_sys', metavar='OS',
            help='change the operating system for this bug')
        self.attr.add_argument(
            '--platform',
            help='change the platform for this bug')
        self.attr.add_argument(
            '--priority',
            help='change the priority for this bug')
        self.attr.add_argument(
            '--product',
            help='change the product for this bug')
        self.attr.add_argument(
            '--see-also', action='csv_negations', metavar='URL',
            help='add/remove "see also" URLs',
            docs="""
                Add or remove "See Also" URLs.

                Use comma-separated values to add or remove URLs for a given
                bug. Use the prefixes '+' and '-' for each value to add and
                remove entries, respectively.
            """)
        person = self.parser.add_argument_group('Person related')
        person.add_argument(
            '-a', '--assigned-to',
            help='change assignee for this bug')
        person.add_argument(
            '--cc', action='csv_negations',
            help='add/remove CCs',
            docs="""
                Add or remove users from the CC list.

                Use comma-separated values to add or remove CCs for a given
                bug. Use the prefixes '+' and '-' for each user to add and
                remove entries, respectively.
            """)
        person.add_argument(
            '--qa-contact',
            help='change the QA contact for this bug')
        status = self.parser.add_argument_group('Status related')
        status.add_argument(
            '-s', '--status',
            help='set new status of bug (e.g. RESOLVED)')
        status.add_argument(
            '-R', '--resolution',
            help='set new resolution')
        status.add_argument(
            '-d', '--duplicate', type=int,
            metavar='BUG_ID', dest='dupe_of',
            help='mark bug as a duplicate')
        time = self.parser.add_argument_group('Time related')
        time.add_argument(
            '--deadline',
            help='change the deadline for this bug')
        time.add_argument(
            '--estimated-time', metavar='TIME',
            help='change the estimated time for this bug')
        time.add_argument(
            '--remaining-time', metavar='TIME',
            help='change the remaining time for this bug')
        time.add_argument(
            '--work-time', metavar='TIME',
            help='set number of hours worked on this bug as part of this change'),


class Search(args.PagedSearch, Bugzilla4_4Opts):

    def add_time_args(self):
        self.time.add_argument(
            '-c', '--created', type='date', metavar='TIME',
            help=f'{self.service.item.type}s created at this time or later')
        self.time.add_argument(
            '-m', '--modified', type='date', metavar='TIME',
            help=f'{self.service.item.type}s modified at this time or later')

    def add_args(self):
        super().add_args()
        # optional args
        self.opts.add_argument(
            '--output',
            help='custom format for search output')

        self.person = self.parser.add_argument_group('Person related')
        self.person.add_argument(
            '-a', '--assigned-to', type='str_list', action='parse_stdin',
            help=f'person the {self.service.item.type} is assigned to')
        self.person.add_argument(
            '-r', '--creator', type='str_list', action='parse_stdin',
            help=f'person who created the {self.service.item.type}')
        self.person.add_argument(
            '--qa-contact', type='str_list', action='parse_stdin',
            help=f'QA contact for the {self.service.item.type}')

        self.time = self.parser.add_argument_group('Time related')
        self.add_time_args()

        self.attr = self.parser.add_argument_group('Attribute related')
        self.attr.add_argument(
            '-s', '--status', type='str_list',
            action='parse_stdin',
            help='restrict by status (one or more)')
        self.attr.add_argument(
            '-V', '--version', type='str_list',
            action='parse_stdin',
            help='restrict by version (one or more)')
        self.attr.add_argument(
            '-W', '--whiteboard', type='str_list',
            action='parse_stdin',
            help='status whiteboard')
        self.attr.add_argument(
            '-C', '--component', type='str_list',
            action='parse_stdin',
            help='restrict by component (one or more)')
        self.attr.add_argument(
            '--alias', type='str_list',
            action='parse_stdin',
            help='unique alias for this bug')
        self.attr.add_argument(
            '--id', type='id_list',
            action=partial(ParseStdin, 'ids'),
            help=f'restrict by {self.service.item.type} ID(s)')
        self.attr.add_argument(
            '--os', type='str_list', dest='op_sys', metavar='OS',
            action='parse_stdin',
            help='restrict by operating system (one or more)')
        self.attr.add_argument(
            '--platform', type='str_list',
            action='parse_stdin',
            help='restrict by platform (one or more)')
        self.attr.add_argument(
            '--priority', type='str_list',
            action='parse_stdin',
            help='restrict by priority (one or more)')
        self.attr.add_argument(
            '--product', type='str_list',
            action='parse_stdin',
            help='restrict by product (one or more)')
        self.attr.add_argument(
            '--resolution', type='str_list',
            action='parse_stdin',
            help='restrict by resolution')
        self.attr.add_argument(
            '--severity', type='str_list',
            action='parse_stdin',
            help='restrict by severity (one or more)')
        self.attr.add_argument(
            '--target-milestone', type='str_list',
            action='parse_stdin',
            help='restrict by target milestone (one or more)')
        self.attr.add_argument(
            '--url', type='str_list',
            action='parse_stdin',
            help='restrict by url (one or more)')


class Search5_0(Search, Bugzilla5_0Opts):

    def add_time_args(self):
        self.time.add_argument(
            '-c', '--created', type='time interval', metavar='TIME_INTERVAL',
            help=f'{self.service.item.type}s created within a specified time interval')
        self.time.add_argument(
            '-m', '--modified', type='time interval', metavar='TIME_INTERVAL',
            help=f'{self.service.item.type}s modified within a specified time interval')

    def add_args(self):
        super().add_args()
        self.opts.add_argument(
            '--sort', action='csv', metavar='TERM',
            help='sorting order for search query',
            docs="""
                Requested sorting order for the given search query.

                Providing multiple sorting terms will give a data response
                sorted by the first term, then the second, and so on.

                Sorting in descending order can be done by prefixing a given
                sorting term with '-'; otherwise, sorting is done in an
                ascending fashion by default.

                Note that if an invalid sorting request is made, bugzilla will
                fall back to its default which is sorting by bug ID. Also, some
                sorting methods such as last-visited require an authenticated
                session to work properly.
            """)

        self.person.add_argument(
            '--cc', type='str_list', action='parse_stdin',
            help='person in the CC list for the bug')
        self.person.add_argument(
            '--commenter', type='str_list', action='parse_stdin',
            help='commenter in the bug')

        self.attr.add_argument(
            '-K', '--keywords', type='str_list',
            action='parse_stdin',
            help='restrict by keywords (one or more)')
        self.attr.add_argument(
            '--blocks', type='id_list',
            action=partial(ParseStdin, 'ids'),
            help='restrict by bug blocks')
        self.attr.add_argument(
            '--depends', type='id_list', dest='depends_on',
            action=partial(ParseStdin, 'ids'),
            help='restrict by bug depends')
        self.attr.add_argument(
            '--votes',
            help='restrict bugs by the specified number of votes or greater')
        self.attr.add_argument(
            '--comments', type=int,
            help='restrict bugs by the specified number of comments or greater')
        self.attr.add_argument(
            '--attachments', nargs='?', type=int, const=1,
            help='restrict bugs by attachment status',
            docs="""
                Search for bugs by their attachment status.

                With no argument, this restricts bugs returned to those that
                have attachments. If passed an argument of '0', returned bugs
                will not have any attachments.
            """)

        self.bugzilla = self.parser.add_argument_group('Bugzilla related')
        self.bugzilla.add_argument(
            '-q', '--quicksearch',
            help='search for bugs using quicksearch syntax',
            docs="""
                Search for bugs using quicksearch syntax.

                See https://bugzilla.mozilla.org/page.cgi?id=quicksearch.html
                and http://www.squarefree.com/bugzilla/quicksearch-help.html
                for a description of the syntax and various examples.
            """)
        self.bugzilla.add_argument(
            '--advanced-url', metavar='URL',
            help='search for bugs using an advanced search URL',
            docs="""
                Search for bugs using URLs from the web UI's advanced search.

                Using this, one can construct any custom search by the advanced
                search interface in the regular web UI and then use the
                resulting URL to peform the same query on the command line.

                Note that options specified on the command line will override
                any matching URL parameters.
            """)
        self.bugzilla.add_argument(
            '-S', '--saved-search',
            help='search for bugs using a saved search')

        self.changes = self.parser.add_argument_group('Change related')
        self.changes.add_argument(
            '--changed', nargs=2, metavar=('FIELD', 'TIME_INTERVAL'),
            action=ChangedTimeTuple,
            help='restrict by changes made during a certain time interval')
        self.changes.add_argument(
            '--changed-from', nargs=2, metavar=('FIELD', 'VALUE'),
            help='restrict by changes from a specified value')
        self.changes.add_argument(
            '--changed-to', nargs=2, metavar=('FIELD', 'VALUE'),
            help='restrict by changes to a specified value')
        self.changes.add_argument(
            '--changed-by', nargs=2, metavar=('FIELD', 'USER'),
            help='restrict by changes made by a specified user')


class APIKeys(args.Subcmd, Bugzilla5_0Opts):
    """generate, revoke, or list API keys"""

    _name = 'apikeys'

    def add_args(self):
        super().add_args()
        action = self.parser.add_argument_group('Action')
        single_action = action.add_mutually_exclusive_group()
        single_action.add_argument(
            '-l', '--list', action='store_true',
            help='list available apikeys')
        single_action.add_argument(
            '-g', '--generate', nargs='?', const='bite', metavar='DESCRIPTION',
            help='generate an apikey')
        single_action.add_argument(
            '-r', '--revoke', action='csv_negations', metavar='KEY',
            help='toggle apikey(s) revoked status',
            docs="""
                Add/remove apikeys from the revoked list using their
                descriptions or values.

                To revoke multiple keys at once, use a comma-separated list.
                Also, prefix an argument with '-' to unrevoke the related key.
            """)


class SavedSearches(args.Subcmd, Bugzilla5_0Opts):
    """save, edit, remove, or list saved searches"""

    _name = 'savedsearches'

    def add_args(self):
        super().add_args()
        action = self.parser.add_argument_group('Action')
        single_action = action.add_mutually_exclusive_group()
        single_action.add_argument(
            '-l', '--list', action='store_true',
            help='list available saved searches')
        single_action.add_argument(
            '-s', '--save', nargs=2, metavar=('NAME', 'URL'),
            help='create a saved search')
        single_action.add_argument(
            '-e', '--edit', nargs='+', metavar='NAME',
            help='edit saved search(es) in the browser')
        single_action.add_argument(
            '-r', '--remove', action='csv', metavar='NAME',
            help='remove saved search(es)')


class Changes(args.Changes, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # optional args
        self.opts.add_argument(
            '-c', '--created', metavar='TIME', type='date',
            help='changes made at this time or later')
        self.opts.add_argument(
            '-m', '--match', type='str_list',
            help='restrict by matching changed fields')
        self.opts.add_argument(
            '--output',
            help='custom format for output')


class Comments(args.Comments, Bugzilla4_4Opts):

    def add_args(self):
        super().add_args()
        # optional args
        self.opts.add_argument(
            '-a', '--attachment', action='store_true',
            help='restrict by comments that include attachments')
        self.opts.add_argument(
            '--output',
            help='custom format for output')


class Version(args.Subcmd, Bugzilla4_4Opts):
    """get bugzilla version"""

    _name = 'version'


class Extensions(args.Subcmd, Bugzilla4_4Opts):
    """get bugzilla extensions"""

    _name = 'extensions'


class Products(args.Subcmd, Bugzilla4_4Opts):
    """get bugzilla products"""

    _name = 'products'

    def add_args(self):
        super().add_args()
        # positional args
        self.parser.add_argument(
            'products', nargs='?', default=None,
            type='str_list', action='parse_stdin',
            help='either ID or name')


class Users(args.Subcmd, Bugzilla4_4Opts):
    """get bugzilla users"""

    _name = 'users'

    def add_args(self):
        super().add_args()
        # positional args
        self.parser.add_argument(
            'users', nargs='+', action='parse_stdin',
            help='either ID, login, or matching string')


class Fields(args.Subcmd, Bugzilla4_4Opts):
    """get bugzilla fields"""

    _name = 'fields'

    def add_args(self):
        super().add_args()
        # positional args
        self.parser.add_argument(
            'fields', nargs='?', default=None,
            type='str_list', action='parse_stdin',
            help='either ID or name')
