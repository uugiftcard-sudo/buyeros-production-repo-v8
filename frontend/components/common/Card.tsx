"use client";

interface CardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function Card({ children, title, className = "" }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-md border ${className}`}>
      {title && (
        <div className="border-b px-4 py-3">
          <h3 className="font-semibold text-lg">{title}</h3>
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
