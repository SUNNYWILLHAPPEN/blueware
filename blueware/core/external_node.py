try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from collections import namedtuple

import blueware.core.trace_node

from blueware.core.metric import TimeMetric

_ExternalNode = namedtuple('_ExternalNode',
        ['library', 'url', 'method', 'children', 'start_time', 'end_time',
        'duration', 'exclusive', 'params'])

class ExternalNode(_ExternalNode):

    @property
    def details(self):
        if hasattr(self, '_details'):
            return self._details

        try:
            self._details = urlparse.urlparse(self.url or '')
        except Exception:
            self._details = urlparse.urlparse('http://unknown.url')

        return self._details

    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this
        external node as well as all the child nodes.

        """

        hostname = self.details.hostname or 'unknown'

        try:
            scheme = self.details.scheme.lower()
            port = self.details.port
        except Exception:
            scheme = None
            port = None

        if (scheme, port) in (('http', 80), ('https', 443)):
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        try:
            # Remove cross_process_id from the params dict otherwise it shows
            # up in the UI.

            self.cross_process_id = self.params.pop('cross_process_id')
            self.external_txn_name = self.params.pop('external_txn_name')
            self.external_exclusive = self.params.pop('external_exclusive')
        except KeyError:
            self.cross_process_id = None
            self.external_txn_name = None
            _exclusive = self.exclusive
        else:
            _exclusive = self.external_exclusive

        yield TimeMetric(name='External/all', scope='',
                duration=self.duration, exclusive=_exclusive)

        if root.type == 'WebTransaction':
            yield TimeMetric(name='External/allWeb', scope='',
                    duration=self.duration, exclusive=_exclusive)
        else:
            yield TimeMetric(name='External/allOther', scope='',
                    duration=self.duration, exclusive=_exclusive)

        if self.cross_process_id is None:
            name = 'External/%s/all' % netloc
            yield TimeMetric(name=name, scope='', duration=self.duration,
                      exclusive=_exclusive)

            method = self.method or ''

            name = 'External/%s/%s/%s' % (netloc, self.library, method)

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=_exclusive)

            yield TimeMetric(name=name, scope=root.path,
                    duration=self.duration, exclusive=_exclusive)

        else:
            name = 'ExternalTransaction/%s/%s/%s' % (netloc,
                    self.cross_process_id, self.external_txn_name)

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=_exclusive)

            yield TimeMetric(name=name, scope=root.path,
                    duration=self.duration, exclusive=_exclusive)

            name = 'ExternalApp/%s/%s/all' % (netloc, self.cross_process_id)

            yield TimeMetric(name=name, scope='', duration=self.duration,
                    exclusive=_exclusive)


    def trace_node(self, stats, root, connections):

        hostname = self.details.hostname or 'unknown'

        try:
            scheme = self.details.scheme.lower()
            port = self.details.port
        except Exception:
            scheme = None
            port = None

        if (scheme, port) in (('http', 80), ('https', 443)):
            port = None

        netloc = port and ('%s:%s' % (hostname, port)) or hostname

        method = self.method or ''

        if self.cross_process_id is None:
            name = 'External/%s/%s/%s' % (netloc, self.library, method)
        else:
            name = 'ExternalTransaction/%s/%s/%s' % (netloc,
                                                     self.cross_process_id,
                                                     self.external_txn_name)

        name = root.string_table.cache(name)

        start_time = blueware.core.trace_node.node_start_time(root, self)
        end_time = blueware.core.trace_node.node_end_time(root, self)

        children = []

        root.trace_node_count += 1

        params = self.params

        details = self.details
        url = urlparse.urlunsplit((details.scheme, details.netloc,
                details.path, '', ''))

        params['url'] = url

        class_name = name
        method_name = ''

        return blueware.core.trace_node.TraceNode(start_time=start_time,
                end_time=end_time, name=name, params=params, children=children,
                label=class_name, method_name=method_name)
