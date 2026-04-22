import React from 'react';
import { AlertCircle, CheckCircle, Info, HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
  text: string;
}

export function HelpTooltip({ text }: HelpTooltipProps) {
  return (
    <span className="relative inline-flex items-center group align-middle ml-1">
      <button
        type="button"
        tabIndex={0}
        aria-label="Help"
        className="inline-flex items-center justify-center w-4 h-4 rounded-full text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600"
      >
        <HelpCircle className="w-4 h-4" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-20 w-56 sm:w-64 px-3 py-2 rounded-md bg-gray-900 text-white text-xs leading-snug shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible group-focus-within:opacity-100 group-focus-within:visible transition-opacity duration-150"
      >
        {text}
      </span>
    </span>
  );
}

interface LabelWithHelpProps {
  label: string;
  tooltip?: string;
}

function LabelWithHelp({ label, tooltip }: LabelWithHelpProps) {
  return (
    <label className="block text-sm font-medium text-gray-700 mb-1">
      <span>{label}</span>
      {tooltip && <HelpTooltip text={tooltip} />}
    </label>
  );
}

interface AlertProps {
  type: 'error' | 'success' | 'info' | 'warning';
  title?: string;
  message: string;
  onClose?: () => void;
  className?: string;
}

export function Alert({ type, title, message, onClose, className = '' }: AlertProps) {
  const bgColor = {
    error: 'bg-red-50 border-red-200',
    success: 'bg-green-50 border-green-200',
    info: 'bg-blue-50 border-blue-200',
    warning: 'bg-yellow-50 border-yellow-200',
  };

  const textColor = {
    error: 'text-red-900',
    success: 'text-green-900',
    info: 'text-blue-900',
    warning: 'text-yellow-900',
  };

  const Icon = type === 'error' ? AlertCircle : type === 'success' ? CheckCircle : Info;

  return (
    <div className={`border rounded-lg p-4 ${bgColor[type]} ${className}`.trim()}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 ${textColor[type]} mt-0.5 flex-shrink-0`} />
        <div className="flex-1">
          {title && <h3 className={`font-semibold ${textColor[type]} mb-1`}>{title}</h3>}
          <p className={textColor[type]}>{message}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseClass = 'font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

  const variantClass = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50',
  };

  const sizeClass = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      {...props}
      className={`${baseClass} ${variantClass[variant]} ${sizeClass[size]} ${className}`.trim()}
      disabled={loading || props.disabled}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  tooltip?: string;
}

export function Input({ label, error, tooltip, ...props }: InputProps) {
  return (
    <div className="w-full">
      {label && <LabelWithHelp label={label} tooltip={tooltip} />}
      <input
        {...props}
        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none ${
          error ? 'border-red-500' : 'border-gray-300'
        }`}
      />
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  tooltip?: string;
  options: Array<{ value: string; label: string }>;
}

export function Select({ label, error, tooltip, options, ...props }: SelectProps) {
  return (
    <div className="w-full">
      {label && <LabelWithHelp label={label} tooltip={tooltip} />}
      <select
        {...props}
        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none ${
          error ? 'border-red-500' : 'border-gray-300'
        }`}
      >
        <option value="">Select an option</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
}

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <div className={`bg-white rounded-lg shadow ${className || ''}`}>{children}</div>;
}

interface BadgeProps {
  label: string;
  variant?: 'success' | 'warning' | 'danger' | 'info';
}

export function Badge({ label, variant = 'info' }: BadgeProps) {
  const variants = {
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
  };

  return <span className={`px-3 py-1 rounded-full text-sm font-medium ${variants[variant]}`}>{label}</span>;
}
