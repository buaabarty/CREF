import clang.cindex
import zss
import uuid
import settings

# 自定义节点类，用于表示 AST 的节点
class ASTNode(object):
    def __init__(self, kind, spelling=''):
        self.kind = kind
        self.spelling = spelling
        self.children = []

    def add_child(self, node):
        self.children.append(node)

# 递归构建简化的 AST 表示
def build_simple_tree(filename, node):
    if node.location.file is not None and node.location.file.name != filename:
        return None
    simple_node = ASTNode(node.kind, node.spelling)
    if len(list(node.get_children())) == 1:
        return build_simple_tree(filename, list(node.get_children())[0])
    for child in node.get_children():
        ret = build_simple_tree(filename, child)
        if ret is not None:
            simple_node.add_child(ret)
    return simple_node

# 自定义标签距离函数
def label_distance(A, B):
    if A == '' or B == '':
        return 1
    return 0 if A[0] == B[0] and A[1] == B[1] else 1

# 函数获取一个节点的子节点
def get_children(node):
    return node.children

# 函数获取一个节点的标签
def get_label(node):
    return (node.kind, node.spelling)

# 计算树的节点数
def count_nodes(tree):
    return 1 + sum(count_nodes(child) for child in tree.children)

# 配置 clang
clang.cindex.Config.set_library_file(settings.llvm_dir)
index = clang.cindex.Index.create()

def calc_dist(code1, code2):
    f1 = open('/tmp/' + str(uuid.uuid4()) + '.cpp', 'w', encoding='utf-8')
    f1.write(code1)
    f1.close()
    f2 = open('/tmp/' + str(uuid.uuid4()) + '.cpp', 'w', encoding='utf-8')
    f2.write(code2)
    f2.close()
    ast1 = index.parse(f1.name).cursor
    ast2 = index.parse(f2.name).cursor

    # 构建简化的 AST 表示
    simple_tree1 = build_simple_tree(f1.name, ast1)
    simple_tree2 = build_simple_tree(f2.name, ast2)
    print(count_nodes(simple_tree1), count_nodes(simple_tree2), flush=True)

    # 计算树编辑距离
    raw_distance = zss.simple_distance(simple_tree1, simple_tree2, get_children, get_label, label_distance)

    # 计算两棵树的节点数
    max_nodes = max(count_nodes(simple_tree1), count_nodes(simple_tree2))

    # 归一化树编辑距离
    normalized_distance = raw_distance / max_nodes
    print('calculate finish', normalized_distance, flush=True)
    
    return normalized_distance
