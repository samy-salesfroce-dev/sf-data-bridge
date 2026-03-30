import networkx as nx
from core.metadata_engine import get_object_fields

def build_dependency_graph(sf_instance, object_list):
    """
    Builds a Directed Acyclic Graph (DAG) for migration ordering.
    Returns:
      - sorted_objects: List of object names in correct migration order.
      - self_references: Dictionary of {object_name: [list of self-referential fields]}
    """
    G = nx.DiGraph()
    self_references = {}
    
    # 1. Add all nodes first
    for obj in object_list:
        G.add_node(obj)
        self_references[obj] = []

    # 2. Add edges based on relationships
    for obj in object_list:
        fields = get_object_fields(sf_instance, obj)
        
        for field_name, attr in fields.items():
            if attr['type'] == 'reference' and attr.get('referenceTo'):
                # Many reference fields can point to multiple objects (Polymorphic),
                # but we usually care about standard single lookups or the primary ones.
                for ref_target in attr['referenceTo']:
                    if ref_target in object_list:
                        if ref_target == obj:
                            # Self-referential loop (e.g. Account.ParentId)
                            self_references[obj].append(field_name)
                        else:
                            # Edge from Parent -> Child (Parent must be created first)
                            # E.g. Account -> Contact
                            G.add_edge(ref_target, obj)
                            
    # 3. Handle Cycles / Topological Sort
    try:
        # topological_sort returns an iterator of nodes such that for every directed edge u -> v, u comes before v.
        sorted_objects = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        # A cycle exists that is NOT self-referential (e.g. A->B->A where A!=B).
        # We will attempt to break the cycle by removing the weakest edges or warn the user.
        # For simplicity in this engine, we fallback to just breaking all cycles forcefully.
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            # Drop the first edge in the cycle to break it
            if len(cycle) > 1:
                G.remove_edge(cycle[0], cycle[1])
                print(f"Cycle detected and broken between {cycle[0]} and {cycle[1]}")
        sorted_objects = list(nx.topological_sort(G))
        
    return sorted_objects, self_references
