import React from 'react';
import { cn } from '@/lib/utils';

// Table container
export interface TableProps {
  children: React.ReactNode;
  className?: string;
}

export const Table: React.FC<TableProps> = ({ children, className }) => {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn('w-full text-sm text-left', className)}>
        {children}
      </table>
    </div>
  );
};

// Table header
export interface TableHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export const TableHeader: React.FC<TableHeaderProps> = ({ children, className }) => {
  return (
    <thead className={cn('text-[#8b949e] border-b border-[#30363d]', className)}>
      {children}
    </thead>
  );
};

// Table body
export interface TableBodyProps {
  children: React.ReactNode;
  className?: string;
}

export const TableBody: React.FC<TableBodyProps> = ({ children, className }) => {
  return (
    <tbody className={cn('divide-y divide-[#30363d]', className)}>
      {children}
    </tbody>
  );
};

// Table row
export interface TableRowProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const TableRow: React.FC<TableRowProps> = ({ children, className, onClick }) => {
  return (
    <tr
      className={cn(
        'transition-colors',
        onClick && 'cursor-pointer hover:bg-[#21262d]',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  );
};

// Table cell
export interface TableCellProps {
  children: React.ReactNode;
  className?: string;
  header?: boolean;
}

export const TableCell: React.FC<TableCellProps> = ({ children, className, header = false }) => {
  const Component = header ? 'th' : 'td';

  return (
    <Component
      className={cn(
        'px-6 py-4',
        header ? 'font-medium text-[#e6edf3] text-xs uppercase tracking-wider' : 'text-[#e6edf3]',
        className
      )}
    >
      {children}
    </Component>
  );
};

/**
 * Table components for displaying tabular data
 * @example
 * <Table>
 *   <TableHeader>
 *     <TableRow>
 *       <TableCell header>Name</TableCell>
 *       <TableCell header>Status</TableCell>
 *     </TableRow>
 *   </TableHeader>
 *   <TableBody>
 *     <TableRow>
 *       <TableCell>Test</TableCell>
 *       <TableCell>Active</TableCell>
 *     </TableRow>
 *   </TableBody>
 * </Table>
 */
