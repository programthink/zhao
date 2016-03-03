#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import shutil
import re
from io import StringIO
import yaml


def _raise_err(format, *args) :
    raise ValueError(format % args)


def _load_yaml(yaml_file) :
    print(u'load: ' + yaml_file)
    with open(yaml_file, u'r') as f :
        return yaml.load(f.read())



class Node :
    all = {}
    keys = []

    @classmethod
    def init(cls) :
        Node.all = {}
        Node.keys = []

        for node_type in [u'person', u'company'] :
            for node_id in os.listdir(u'../data/' + node_type) :
                yaml_file = u'../data/%s/%s/brief.yaml' % (node_type, node_id)
                node = Node(_load_yaml(yaml_file), node_id, node_type)
                if node_id in Node.all :
                    _raise_err(u'Node id conflict: "%s"!', node_id)

                Node.all[node_id] = node
                Node.keys.append(node_id)
        print(u'Node number: %d' % len(Node.all))


    def __init__(self, yaml, node_id, type) :
        self.id = node_id
        self.type = type
        self.name = yaml[u'name']
        if u'other_names' in yaml :  # person
            self.other_names = yaml[u'other_names']
        if u'sex' in yaml :  # person
            self.sex = yaml[u'sex']
        if u'full_name' in yaml :  # company
            self.full_name = yaml[u'full_name']
        self.birth = yaml[u'birth']
        self.death = yaml[u'death']
        self.desc = yaml[u'desc']
        self.links = yaml[u'links']



class Relation :
    all = {}
    keys = []

    @classmethod
    def init(cls) :
        for family_id in os.listdir(u'../data/family/') :
            family_id = family_id.replace(u'.yaml', u'')
            yaml_file = u'../data/family/%s.yaml' % (family_id,)
            if family_id not in Node.all :
                _raise_err(u'Invalid family name: "%s"!', family_id)

            yaml = _load_yaml(yaml_file)
            for lst in yaml[u'relations'] :
                relation = Relation(lst)
                Relation.all[relation.name] = relation
                Relation.keys.append(relation.name)
        print(u'Relation number: %d' % len(Relation.all))


    def __init__(self, lst) :
        self.node_from = lst[0]
        self.node_to = lst[1]
        self.desc = lst[2]
        self.name = self.node_from + u'->' + self.node_to

        if self.name in Relation.all :
            _raise_err(u'Relation name conflict: "%s"!', self.name)
        if self.node_from not in Node.all :
            _raise_err(u'Invalid relation "from" attr: "%s"!', self.node_from)
        if self.node_to not in Node.all :
            _raise_err(u'Invalid relation "to" attr": "%s"!', self.node_to)



class Family :
    all = {}
    keys = []

    @classmethod
    def init(cls) :
        for family_id in os.listdir(u'../data/family/') :
            family_id = family_id.replace(u'.yaml', u'')
            yaml_file = u'../data/family/%s.yaml' % (family_id,)
            if family_id not in Node.all :
                _raise_err(u'Invalid family name: "%s"!', family_id)

            family = Family(_load_yaml(yaml_file))
            Family.all[family_id] = family
            Family.keys.append(family_id)
        print(u'Family number: %d' % len(Family.all))


    def __init__(self, yaml) :
        self.name = yaml[u'name']
        self.inner = yaml[u'inner']
        self.outer = yaml[u'outer']
        self.members = [self.name] + self.inner + self.outer

        for name in self.members :
            if name not in Node.all :
                _raise_err(u'Invalid family members: "%s"!', name)



class Graph :
    def __init__(self, yaml) :
        self._name = yaml[u'name']
        self._families = yaml[u'families']
        self._families.reverse()
        self._nodes = []
        self._relations = []
        for f in self._families :
            family = Family.all[f]
            for n in family.members :
                if n not in self._nodes :
                    self._nodes.append(n)
            for r in Relation.keys :
                relation = Relation.all[r]
                if relation.node_from in family.members \
                    and relation.node_to in family.members \
                    and r not in self._relations :
                    self._relations.append(r)


    def dump(self) :
        output = StringIO()

        for n in self._nodes :
            output.write(self._dot_node(n))
        output.write(u'\n')

        for r in self._relations :
            output.write(self._dot_relation(r))
        output.write(u'\n')

        if len(self._families) > 1 :
            for f in self._families :
                output.write(self._dot_sub_graph(f))

        template = u'''
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


    def _node_color(self, node) :
        if u'company' == node.type :
            return u'green'
        else :
            return (u'blue' if u'M'==node.sex else u'red')

    def _other_names(self, node) :
        other_names = ''
        if u'person'==node.type and node.other_names :
            other_names = u', '.join([u'%s:%s' % (k,v) for k,v in node.other_names.items()])
        elif u'company'==node.type and node.full_name :
            other_names = node.full_name
        return u'<tr><td>(%s)</td></tr>' % (other_names,) if other_names else ''

    def _dot_node(self, node_id) :
        node = Node.all[node_id]
        template = u'\t%s [shape="%s", color="%s", ' \
                    u'label=<<table border="0" cellborder="0">' \
                    u'<tr><td>%s%s</td></tr>' \
                    u'%s' \
                    u'<tr><td>%s</td></tr>' \
                    u'<tr><td>%s</td></tr></table>>];\n'

        portrait = u'../data/person/%s/portrait.png' % (node_id,)
        portrait = u'<img src="%s"/>' % (portrait,) if os.path.exists(portrait) else ''

        return template % (node.id,
                           u'box' if u'person'==node.type else u'ellipse',
                           self._node_color(node),
                           node.name,
                           (u'' if node.birth==u'N/A' else u' [%s]'%node.birth),
                           self._other_names(node),
                           portrait,
                           node.desc.replace(u'\n', u'<br/>'))


    def _dot_relation(self, name) :
        relation = Relation.all[name]
        template = u'''\t%s -> %s [label="%s", style=%s, color="%s"];\n'''

        if re.match(u'^夫|妻$', relation.desc) :
            style = u'bold'
        elif re.match(u'^父|母$', relation.desc) :
            style = u'solid'
        elif re.match(u'^(独|长|次|三|四|五|六|七)?(子|女)$', relation.desc) :
            style = u'solid'
        elif re.match(u'^.*?(兄|弟|姐|妹)$', relation.desc) :
            style = u'dashed'
        else :
            style = u'dotted'

        return template % (relation.node_from, relation.node_to,
                           relation.desc, style,
                           self._node_color(Node.all[relation.node_to]))


    def _dot_sub_graph(self, name) :
        node = Node.all[name]
        if node.type == u'company' :
            return self._dot_node(name)

        family = Family.all[name]
        template = u'''
\tsubgraph "cluster_%s"
\t{
\t\tfontsize="18";
\t\tlabel="%s家族";
\t\t%s;
\t}
'''
        return template % (family.name, family.name,
                           u';'.join([name]+family.inner))



class Builder :
    def __init__(self) :
        Node.init()
        Relation.init()
        Family.init()

    def _mkdir(self, name) :
        if os.path.exists(name) :
            shutil.rmtree(name)
        os.mkdir(name)

    def _exec(self, cmd) :
        print(cmd)
        return os.system(cmd.encode(u'utf-8'))

    def do(self, file_type) :
        os.chdir(u'../download/')
        self._mkdir(u'dot')
        self._mkdir(file_type)
        n = 0
        for graph in _load_yaml(u'../data/graph.yaml') :
            n += 1
            name = u'%02d-%s' % (n, graph[u'name'])
            dot_file = u'./dot/%s.dot' % (name,)
            output_file = u'./%s/%s.%s' % (file_type, name, file_type)

            with open(dot_file, u'wb') as f :
                f.write(Graph(graph).dump().encode(u'utf-8'))

            cmd = u'dot "%s" -T%s -o"%s"' % (dot_file, file_type, output_file)
            if self._exec(cmd) != 0 :
                _raise_err(u'Make "%s" failed!', dot_file)
        return 0


if '__main__' == __name__ :
    try :
        if len(sys.argv) != 2 :
            print(u'''Usage:\n%s file_type
(file_type is pdf or jpg or png or gif or tiff or svg or ps)''' % sys.argv[0])
            sys.exit(0)
        sys.exit(Builder().do(sys.argv[1]))
    except Exception as err :
        print(u'Make abort!\n%s' % err)
        sys.exit(1)
