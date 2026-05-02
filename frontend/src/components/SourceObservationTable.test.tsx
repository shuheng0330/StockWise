import { renderToStaticMarkup } from 'react-dom/server';

import { SourceObservationTable } from './SourceObservationTable';

describe('SourceObservationTable', () => {
  it('renders every uploaded source observation across months', () => {
    const html = renderToStaticMarkup(
      <SourceObservationTable
        observations={[
          {
            date: '2025-06-10',
            item_id: 1,
            item_name: 'Paneer',
            current_stock: 12,
            unit: 'kg',
            usage_value: 2,
            usage_period: 'daily',
            lead_time_days: 3,
            price_per_unit: 450,
            seasonal_factor: 1.1,
            supplier_name: 'Supplier A',
          },
          {
            date: '2025-07-10',
            item_id: 1,
            item_name: 'Paneer',
            current_stock: 4,
            unit: 'kg',
            usage_value: 5,
            usage_period: 'daily',
            lead_time_days: 3,
            price_per_unit: 450,
            seasonal_factor: 1.1,
            supplier_name: 'Supplier A',
          },
        ]}
      />
    );

    expect(html).toContain('Source Upload History');
    expect(html).toContain('2025-06-10');
    expect(html).toContain('2025-07-10');
    expect(html).toContain('12 kg');
    expect(html).toContain('4 kg');
    expect(html).toContain('2 daily');
    expect(html).toContain('5 daily');
  });
});
