"""
Topic-Aware Sampling Graph for the Karl self-improvement flywheel.

Tracks selection frequency across a hierarchical concept tree so the
problem generator always picks the least-represented leaf topic next,
driving even coverage across the training curriculum.
"""


class TopicNode:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.frequency = 0


class DynamicTopicGraph:
    def __init__(self):
        self.root = TopicNode("root")

        math_node   = TopicNode("math",   self.root)
        coding_node = TopicNode("coding", self.root)

        self.leaves = [
            TopicNode("algebra_3var",        math_node),
            TopicNode("quadratics",          math_node),
            TopicNode("parentheses_matching", coding_node),
            TopicNode("matrix_transposition", coding_node),
            TopicNode("anagrams",            coding_node),
        ]

    def get_underrepresented_topic(self) -> str:
        """Return the leaf name with the lowest selection frequency and increment it."""
        under = min(self.leaves, key=lambda node: node.frequency)
        under.frequency += 1
        return under.name

    def frequencies(self) -> dict[str, int]:
        """Return a snapshot of current leaf frequencies (useful for logging/debugging)."""
        return {node.name: node.frequency for node in self.leaves}
