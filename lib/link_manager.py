"""Utilities for managing links inside drawio diagrams."""

import xml.etree.ElementTree as ET


def find_parent(root, target):
    """Return parent element for ``target`` inside ``root`` tree."""
    for elem in root.iter():
        for child in list(elem):
            if child is target:
                return elem
    return None


def remove_all_links(diagram):
    """Remove all existing links from diagram.

    Parameters
    ----------
    diagram : drawio_diagram
        Diagram object from N2G library.

    Returns
    -------
    list[tuple[str, str]]
        List of tuples representing removed connections as ``(source, target)``.
    """

    root = diagram.drawing
    removed_links = []

    # Iterate over a snapshot of objects to safely modify tree while iterating
    for obj in list(root.iter('object')):
        cell = obj.find('mxCell')
        if cell is not None and cell.get('edge') == '1':
            source = cell.get('source')
            target = cell.get('target')
            if source and target:
                removed_links.append((source, target))
                parent = find_parent(root, obj)
                if parent is not None:
                    parent.remove(obj)

    return removed_links


def count_links(diagram):
    """Count links currently present in the diagram."""

    root = diagram.drawing
    count = 0
    for obj in root.iter('object'):
        cell = obj.find('mxCell')
        if cell is not None and cell.get('edge') == '1':
            count += 1
    return count

