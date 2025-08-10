// Core types for JARVIS HUD
export interface Particle {
  id: number;
  x: number;
  y: number;
  z: number;
  speed: number;
  size: number;
}

export interface Todo {
  id: string;
  text: string;
  done: boolean;
}

export interface Weather {
  temp: number;
  desc: string;
}

export interface SystemMetrics {
  cpu: number;
  mem: number;
  net: number;
}

export type ModuleName = "calendar" | "mail" | "finance";

export interface HUDState {
  activeModule: ModuleName | null;
}

export interface VoiceInput {
  transcript: string;
  isListening: boolean;
  start: () => void;
}

// SVG Icon Props
export interface SvgProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

// HUD Button Props
export interface HUDButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
}

// Pane Props
export interface PaneProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

// Metric Props
export interface MetricProps {
  label: string;
  value: number;
  icon: React.ReactNode;
}

// TodoList Props
export interface TodoListProps {
  todos: Todo[];
  onToggle: (id: string) => void;
  onRemove: (id: string) => void;
  onAdd: (text: string) => void;
}
