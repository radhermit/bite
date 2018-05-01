from .bugzilla import date
from .. import args


class TracOpts(args.ServiceOpts):
    pass


class TracJsonrpcOpts(TracOpts):

    _service = 'trac-jsonrpc'


class TracXmlrpcOpts(TracOpts):

    _service = 'trac-xmlrpc'


@args.subcmd(TracOpts)
class Search(args.Search):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.opts.add_argument(
            '--sort', dest='order', metavar='TERM',
            help='sorting order for search query',
            docs="""
                Requested sorting order for the given search query.

                Sorting in descending order can be done by prefixing a given
                sorting term with '-'; otherwise, sorting is done in an
                ascending fashion by default.

                Note that sorting by multiple terms is not supported.
            """)
        time = self.parser.add_argument_group('Time related')
        time.add_argument(
            '-c', '--created', type=date, metavar='TIME',
            help=f'{self.service.item.type}s created at this time or later')
        time.add_argument(
            '-m', '--modified', type=date, metavar='TIME',
            help=f'tickets modified at this time or later')
