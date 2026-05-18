import type { ButtonHTMLAttributes, ReactNode } from "react";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: "default" | "primary" | "danger";
  children: ReactNode;
}

export function IconButton({
  label,
  variant = "default",
  className = "",
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      {...props}
      aria-label={label}
      className={`icon-button icon-button--${variant} ${className}`}
      title={label}
      type={props.type ?? "button"}
    >
      {children}
    </button>
  );
}
