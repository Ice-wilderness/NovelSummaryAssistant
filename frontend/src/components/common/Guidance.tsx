import { Info } from "lucide-react";
import type { ReactNode } from "react";

interface GuidancePanelProps {
  title: string;
  children?: ReactNode;
  items?: string[];
}

export function GuidancePanel({ title, children, items }: GuidancePanelProps) {
  return (
    <section className="guidance-panel" aria-label={title}>
      <header>
        <Info size={17} />
        <strong>{title}</strong>
      </header>
      {children ? <p>{children}</p> : null}
      {items?.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
