import * as ScrollArea from "@radix-ui/react-scroll-area";
import * as Tabs from "@radix-ui/react-tabs";
import * as Tooltip from "@radix-ui/react-tooltip";
import { motion, type HTMLMotionProps } from "framer-motion";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  ReactNode
} from "react";

export type StudioTone =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "muted";

function classNames(...items: Array<string | false | null | undefined>) {
  return items.filter(Boolean).join(" ");
}

interface StudioPanelProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function StudioPanel({
  title,
  description,
  actions,
  children,
  className = "",
  ...props
}: StudioPanelProps) {
  return (
    <section className={classNames("studio-panel", className)} {...props}>
      {title || description || actions ? (
        <header className="studio-panel__header">
          <div>
            {title ? <h3>{title}</h3> : null}
            {description ? <p>{description}</p> : null}
          </div>
          {actions ? <div className="studio-panel__actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="studio-panel__body">{children}</div>
    </section>
  );
}

interface StudioCardProps extends HTMLAttributes<HTMLElement> {
  tone?: StudioTone;
  children: ReactNode;
}

export function StudioCard({
  tone = "neutral",
  className = "",
  children,
  ...props
}: StudioCardProps) {
  return (
    <article className={classNames("studio-card", `studio-card--${tone}`, className)} {...props}>
      {children}
    </article>
  );
}

interface StudioStatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: StudioTone;
  children: ReactNode;
}

export function StudioStatusBadge({
  tone = "neutral",
  className = "",
  children,
  ...props
}: StudioStatusBadgeProps) {
  return (
    <span className={classNames("studio-status", `studio-status--${tone}`, className)} {...props}>
      <span className="studio-status__dot" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}

interface StudioButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  children: ReactNode;
}

export function StudioButton({
  variant = "secondary",
  className = "",
  children,
  ...props
}: StudioButtonProps) {
  return (
    <button
      className={classNames("studio-button", `studio-button--${variant}`, className)}
      type={props.type ?? "button"}
      {...props}
    >
      {children}
    </button>
  );
}

interface StudioTooltipProps {
  content: ReactNode;
  children: ReactNode;
}

export function StudioTooltip({ content, children }: StudioTooltipProps) {
  return (
    <Tooltip.Provider delayDuration={220}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content className="studio-tooltip" sideOffset={8}>
            {content}
            <Tooltip.Arrow className="studio-tooltip__arrow" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

export interface StudioTabItem {
  key: string;
  label: string;
  meta?: string;
  content: ReactNode;
}

interface StudioTabsProps {
  label: string;
  items: StudioTabItem[];
  value: string;
  onValueChange: (value: string) => void;
}

export function StudioTabs({
  label,
  items,
  value,
  onValueChange
}: StudioTabsProps) {
  return (
    <Tabs.Root className="studio-tabs" value={value} onValueChange={onValueChange}>
      <Tabs.List className="studio-tabs__list" aria-label={label}>
        {items.map((item) => (
          <Tabs.Trigger className="studio-tabs__trigger" value={item.key} key={item.key}>
            <span>{item.label}</span>
            {item.meta ? <small>{item.meta}</small> : null}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {items.map((item) => (
        <Tabs.Content className="studio-tabs__content" value={item.key} key={item.key}>
          {item.content}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}

interface StudioScrollAreaProps {
  className?: string;
  children: ReactNode;
}

export function StudioScrollArea({ className = "", children }: StudioScrollAreaProps) {
  return (
    <ScrollArea.Root className={classNames("studio-scroll", className)}>
      <ScrollArea.Viewport className="studio-scroll__viewport">{children}</ScrollArea.Viewport>
      <ScrollArea.Scrollbar className="studio-scroll__bar" orientation="vertical">
        <ScrollArea.Thumb className="studio-scroll__thumb" />
      </ScrollArea.Scrollbar>
      <ScrollArea.Corner className="studio-scroll__corner" />
    </ScrollArea.Root>
  );
}

export function StudioMotionSurface({
  className = "",
  children,
  ...props
}: HTMLMotionProps<"section">) {
  return (
    <motion.section
      className={classNames("studio-motion-surface", className)}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      {...props}
    >
      {children}
    </motion.section>
  );
}
