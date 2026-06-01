"use client";

interface StatusCardProps {
  title: string;
  value: string | number;
  color?: string;
}

export function StatusCard({ title, value, color = "blue" }: StatusCardProps) {
  return (
    <div className={`card border-l-4 border-${color}-500`}>
      <h3 className="text-sm text-gray-500">{title}</h3>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
