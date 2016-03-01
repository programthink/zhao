#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys
import os
import shutil
import re
from io import StringIO
import yaml


def _raise_err(format, *args):
    raise ValueError(format % args)


def _load_yaml(yaml_file):
    print(('load: ' + yaml_file))
    with open(yaml_file, 'r') as f:
        return yaml.load(f.read())


def _exec(cmd):
    print(cmd)
    return os.system(cmd)


class Node:
    all = {}
    keys = []

    @classmethod
    def init(cls):
        Node.all = {}
        Node.keys = []

        for node_type in ['person', 'company']:
            for node_id in os.listdir('../data/' + node_type):
                yaml_file = '../data/%s/%s/brief.yaml' % (node_type, node_id)
                node = Node(_load_yaml(yaml_file), node_id, node_type)
                if node_id in Node.all:
                    _raise_err('Node id conflict: "%s"!', node_id)

                Node.all[node_id] = node
                Node.keys.append(node_id)
        print(('Node number: %d' % len(Node.all)))

    def __init__(self, yaml, node_id, type):
        self.id = node_id
        self.type = type
        self.name = yaml['name']
        if 'other_names' in yaml:  # person
            self.other_names = yaml['other_names']
        if 'sex' in yaml:  # person
            self.sex = yaml['sex']
        if 'full_name' in yaml:  # company
            self.full_name = yaml['full_name']
        self.birth = yaml['birth']
        self.death = yaml['death']
        self.desc = yaml['desc']
        self.links = yaml['links']


class Relation:
    all = {}
    keys = []

    @classmethod
    def init(cls):
        for family_id in os.listdir('../data/family/'):
            family_id = family_id.replace('.yaml', '')
            yaml_file = '../data/family/%s.yaml' % (family_id,)
            if family_id not in Node.all:
                _raise_err('Invalid family name: "%s"!', family_id)

            yaml = _load_yaml(yaml_file)
            for lst in yaml['relations']:
                relation = Relation(lst)
                Relation.all[relation.name] = relation
                Relation.keys.append(relation.name)
        print(('Relation number: %d' % len(Relation.all)))

    def __init__(self, lst):
        self.node_from = lst[0]
        self.node_to = lst[1]
        self.desc = lst[2]
        self.name = self.node_from + '->' + self.node_to

        if self.name in Relation.all:
            _raise_err('Relation name conflict: "%s"!', self.name)
        if self.node_from not in Node.all:
            _raise_err('Invalid relation "from" attr: "%s"!', self.node_from)
        if self.node_to not in Node.all:
            _raise_err('Invalid relation "to" attr": "%s"!', self.node_to)


class Family:
    all = {}
    keys = []

    @classmethod
    def init(cls):
        for family_id in os.listdir('../data/family/'):
            family_id = family_id.replace('.yaml', '')
            yaml_file = '../data/family/%s.yaml' % (family_id,)
            if family_id not in Node.all:
                _raise_err('Invalid family name: "%s"!', family_id)

            family = Family(_load_yaml(yaml_file))
            Family.all[family_id] = family
            Family.keys.append(family_id)
        print(('Family number: %d' % len(Family.all)))

    def __init__(self, yaml):
        self.name = yaml['name']
        self.inner = yaml['inner']
        self.outer = yaml['outer']
        self.members = [self.name] + self.inner + self.outer

        for name in self.members:
            if name not in Node.all:
                _raise_err('Invalid family members: "%s"!', name)


class Graph:

    def __init__(self, yaml):
        self._name = yaml['name']
        self._families = yaml['families']
        self._families.reverse()
        self._nodes = []
        self._relations = []
        for f in self._families:
            family = Family.all[f]
            for n in family.members:
                if n not in self._nodes:
                    self._nodes.append(n)
            for r in Relation.keys:
                relation = Relation.all[r]
                if relation.node_from in family.members \
                        and relation.node_to in family.members \
                        and r not in self._relations:
                    self._relations.append(r)

    def __str__(self):
        output = StringIO()

        for n in self._nodes:
            output.write(self._dot_node(n))
        output.write('\n')

        for r in self._relations:
            output.write(self._dot_relation(r))
        output.write('\n')

        if len(self._families) > 1:
            for f in self._families:
                output.write(self._dot_sub_graph(f))

        template = '''
digraph %s
{
\trankdir = "LR";
\tranksep = 0.5;
\tlabel = "%s";
\tlabelloc = "t";
\tfontsize = "24";
\tfontname = "SimHei";

\tgraph [style="filled", color="lightgrey"];
\tnode [fontname="SimSun"];
\tedge [fontname="SimSun"];

%s
}
'''
        return template % (self._name, self._name, output.getvalue())

    def _node_color(self, node):
        if 'company' == node.type:
            return 'green'
        else:
            return ('blue' if 'M' == node.sex else 'red')

    def _other_names(self, node):
        other_names = ''
        if 'person' == node.type and node.other_names:
            other_names = ', '.join(['%s:%s' % (k, v)
                                     for k, v in list(node.other_names.items())])
        elif 'company' == node.type and node.full_name:
            other_names = node.full_name
        return '<tr><td>(%s)</td></tr>' % (other_names,) if other_names else ''

    def _dot_node(self, node_id):
        node = Node.all[node_id]
        template = '''\t%s [shape="%s", color="%s", ''' \
            '''label=<<table border="0" cellborder="0">''' \
            '''<tr><td>%s%s</td></tr>''' \
            '''%s''' \
            '''<tr><td>%s</td></tr>''' \
            '''<tr><td>%s</td></tr></table>>];\n'''

        portrait = '../data/person/%s/portrait.png' % (node_id,)
        portrait = '<img src="%s"/>' % (portrait,
                                        ) if os.path.exists(portrait) else ''

        return template % (node.id,
                           'box' if 'person' == node.type else 'ellipse',
                           self._node_color(node),
                           node.name,
                           ('' if node.birth ==
                            'N/A' else ' [%s]' % node.birth),
                           self._other_names(node),
                           portrait,
                           node.desc.replace('\n', '<br/>'))

    def _dot_relation(self, name):
        relation = Relation.all[name]
        template = '''\t%s -> %s [label="%s", style=%s, color="%s"];\n'''

        if re.match(r'^夫|妻$', relation.desc):
            style = 'bold'
        elif re.match(r'^父|母$', relation.desc):
            style = 'solid'
        elif re.match(r'^(独|长|次|三|四|五|六|七)?(子|女)$', relation.desc):
            style = 'solid'
        elif re.match(r'^.*?(兄|弟|姐|妹)$', relation.desc):
            style = 'dashed'
        else:
            style = 'dotted'

        return template % (relation.node_from, relation.node_to,
                           relation.desc, style,
                           self._node_color(Node.all[relation.node_to]))

    def _dot_sub_graph(self, name):
        node = Node.all[name]
        if node.type == 'company':
            return self._dot_node(name)

        family = Family.all[name]
        template = '''
\tsubgraph "cluster_%s"
\t{
\t\tfontsize="18";
\t\tlabel="%s家族";
\t\t%s;
\t}
'''
        return template % (family.name, family.name,
                           ';'.join([name] + family.inner))


class Builder:

    def __init__(self):
        Node.init()
        Relation.init()
        Family.init()

    def _mkdir(self, name):
        if os.path.exists(name):
            shutil.rmtree(name)
        os.mkdir(name)

    def do(self, file_type):
        os.chdir('../download/')
        self._mkdir('dot')
        self._mkdir(file_type)

        n = 0
        for graph in _load_yaml('../data/graph.yaml'):
            n += 1
            name = '%02d-%s' % (n, graph['name'])
            dot_file = './dot/%s.dot' % (name,)
            output_file = './%s/%s.%s' % (file_type, name, file_type)

            with open(dot_file, 'w') as f:
                f.write(str(Graph(graph)))

            cms = 'dot %s -T%s -o%s' % (dot_file, file_type, output_file)
            if _exec(cms) != 0:
                _raise_err('Make "%s" failed!' % dot_file)
        return 0


if '__main__' == __name__:
    try:
        if len(sys.argv) != 2:
            print(('''Usage:\n%s file_type
    (file_type is pdf or jpg or png or gif or tiff or svg or ps)''' % sys.argv[0]))
            sys.exit(0)
        file_type = sys.argv[1]
        sys.exit(Builder().do(file_type))
    except Exception as err:
        print(('Make abort!\n%s' % str(err)))
        sys.exit(1)
