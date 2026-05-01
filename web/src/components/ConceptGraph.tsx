import CytoscapeComponent from "react-cytoscapejs";
import type { ConceptNode } from "../api/hooks/useLessons";
import { useEffect, useRef } from "react";
import type cytoscape from "cytoscape";

const STYLE: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "background-color": "#2563eb",
      color: "#fff",
      "font-size": "11px",
      "text-valign": "center",
      "text-halign": "center",
      width: 120,
      height: 40,
      shape: "roundrectangle",
      "text-wrap": "wrap",
      "text-max-width": "110px",
    },
  },
  {
    selector: "node.selected",
    style: { "background-color": "#7c3aed" },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#555",
      "target-arrow-color": "#555",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
    },
  },
];

type Props = {
  concepts: ConceptNode[];
  selectedId?: string;
  onSelect?: (id: string) => void;
};

export default function ConceptGraph({ concepts, selectedId, onSelect }: Props) {
  const cyRef = useRef<cytoscape.Core | null>(null);

  const elements = [
    ...concepts.map((c) => ({
      data: { id: c.id, label: c.title },
    })),
    ...concepts.flatMap((c) =>
      (c.prerequisites ?? []).map((prereqId) => ({
        data: {
          id: `${prereqId}-${c.id}`,
          source: prereqId,
          target: c.id,
        },
      })),
    ),
  ];

  useEffect(() => {
    if (!cyRef.current) return;
    cyRef.current.nodes().removeClass("selected");
    if (selectedId) {
      cyRef.current.getElementById(selectedId).addClass("selected");
    }
  }, [selectedId]);

  return (
    <CytoscapeComponent
      elements={elements}
      style={{ width: "100%", height: "100%" }}
      stylesheet={STYLE}
      layout={{ name: "breadthfirst", directed: true, padding: 20 }}
      cy={(cy) => {
        cyRef.current = cy;
        cy.on("tap", "node", (evt) => {
          const id = evt.target.id() as string;
          onSelect?.(id);
        });
      }}
    />
  );
}
