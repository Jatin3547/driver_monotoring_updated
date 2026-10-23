import type { ReactNode } from 'react';

export interface TableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
}

interface TableProps<T> {
  columns: TableColumn<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

export function Table<T>({ columns, rows, getRowId, onRowClick, emptyMessage = 'No records found.' }: TableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-text-muted border border-dashed border-border rounded-lg">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto -mx-5 px-5">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                style={{ width: col.width }}
                className="text-left font-medium text-text-muted text-xs uppercase tracking-wide py-2.5 px-3 first:pl-0"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={getRowId(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-border last:border-0 ${
                onRowClick ? 'cursor-pointer hover:bg-surface-inset' : ''
              }`}
            >
              {columns.map((col) => (
                <td key={col.key} className="py-3 px-3 first:pl-0 text-text-primary align-middle">
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
