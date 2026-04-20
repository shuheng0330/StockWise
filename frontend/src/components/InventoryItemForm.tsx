import React, { useState } from 'react';
import { Input, Select, Button, Alert } from './common';
import { ManualItemInput, PerishabilityLevel, UsagePeriod } from '@/types';

interface InventoryItemFormProps {
  onSubmit: (items: ManualItemInput[]) => void;
  isLoading?: boolean;
  submitLabel?: string;
}

export function InventoryItemForm({
  onSubmit,
  isLoading = false,
  submitLabel = 'Add Item',
}: InventoryItemFormProps) {
  const [items, setItems] = useState<ManualItemInput[]>([
    {
      item_name: '',
      current_stock: 0,
      unit: '',
      usage_value: 0,
      usage_period: 'daily',
      lead_time_days: 1,
      price_per_unit: 0,
      seasonal_factor: 1.0,
    },
  ]);

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleItemChange = (
    index: number,
    field: keyof ManualItemInput,
    value: any
  ) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
    // Clear error for this field
    if (errors[`${index}-${field}`]) {
      const newErrors = { ...errors };
      delete newErrors[`${index}-${field}`];
      setErrors(newErrors);
    }
  };

  const validateItems = (): boolean => {
    const newErrors: Record<string, string> = {};

    items.forEach((item, index) => {
      if (!item.item_name.trim()) {
        newErrors[`${index}-item_name`] = 'Item name is required';
      }
      if (item.current_stock < 0) {
        newErrors[`${index}-current_stock`] = 'Stock must be >= 0';
      }
      if (!item.unit.trim()) {
        newErrors[`${index}-unit`] = 'Unit is required';
      }
      if (item.usage_value <= 0) {
        newErrors[`${index}-usage_value`] = 'Usage value must be > 0';
      }
      if (item.lead_time_days <= 0) {
        newErrors[`${index}-lead_time_days`] = 'Lead time must be > 0';
      }
      if (item.price_per_unit < 0) {
        newErrors[`${index}-price_per_unit`] = 'Price must be >= 0';
      }
      if (item.seasonal_factor < 0) {
        newErrors[`${index}-seasonal_factor`] = 'Seasonal factor must be >= 0';
      }
      // Check waste signal
      if (!item.perishability_level && !item.recent_waste_percentage) {
        newErrors[`${index}-waste`] = 'Please provide either perishability level or waste percentage';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleAddItem = () => {
    setItems([
      ...items,
      {
        item_name: '',
        current_stock: 0,
        unit: '',
        usage_value: 0,
        usage_period: 'daily',
        lead_time_days: 1,
        price_per_unit: 0,
        seasonal_factor: 1.0,
      },
    ]);
  };

  const handleDuplicateItem = (index: number) => {
    const newItem = { ...items[index] };
    setItems([...items.slice(0, index + 1), newItem, ...items.slice(index + 1)]);
  };

  const handleRemoveItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateItems()) {
      onSubmit(items);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {items.map((item, index) => (
        <div key={index} className="border rounded-lg p-6 bg-gray-50">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Item {index + 1}</h3>
            <div className="flex gap-2">
              {items.length > 1 && (
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={() => handleRemoveItem(index)}
                >
                  Remove
                </Button>
              )}
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => handleDuplicateItem(index)}
              >
                Duplicate
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <Input
              label="Item Name *"
              placeholder="e.g., Fresh Milk"
              value={item.item_name}
              onChange={(e) => handleItemChange(index, 'item_name', e.target.value)}
              error={errors[`${index}-item_name`]}
            />
            <Input
              label="Current Stock *"
              type="number"
              min="0"
              value={item.current_stock}
              onChange={(e) => handleItemChange(index, 'current_stock', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-current_stock`]}
            />
            <Input
              label="Unit *"
              placeholder="e.g., liter, kg, pieces"
              value={item.unit}
              onChange={(e) => handleItemChange(index, 'unit', e.target.value)}
              error={errors[`${index}-unit`]}
            />
            <Input
              label="Usage Value *"
              type="number"
              step="0.01"
              min="0.01"
              value={item.usage_value}
              onChange={(e) => handleItemChange(index, 'usage_value', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-usage_value`]}
            />
            <Select
              label="Usage Period *"
              value={item.usage_period}
              onChange={(e) => handleItemChange(index, 'usage_period', e.target.value as UsagePeriod)}
              options={[
                { value: 'daily', label: 'Daily' },
                { value: 'weekly', label: 'Weekly' },
              ]}
            />
            <Input
              label="Lead Time (days) *"
              type="number"
              min="1"
              value={item.lead_time_days}
              onChange={(e) => handleItemChange(index, 'lead_time_days', parseFloat(e.target.value) || 1)}
              error={errors[`${index}-lead_time_days`]}
            />
            <Input
              label="Price per Unit *"
              type="number"
              step="0.01"
              min="0"
              value={item.price_per_unit}
              onChange={(e) => handleItemChange(index, 'price_per_unit', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-price_per_unit`]}
            />
            <Select
              label="Seasonal Factor *"
              value={item.seasonal_factor.toString()}
              onChange={(e) => handleItemChange(index, 'seasonal_factor', parseFloat(e.target.value))}
              options={[
                { value: '0.8', label: 'Low demand (0.8)' },
                { value: '1.0', label: 'Normal (1.0)' },
                { value: '1.2', label: 'Busy (1.2)' },
                { value: '1.4', label: 'Peak (1.4)' },
              ]}
            />
          </div>

          <div className="border-t pt-4 mb-4">
            <h4 className="font-medium text-gray-900 mb-3">Waste Signal (required - provide at least one)</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Perishability Level"
                value={item.perishability_level || ''}
                onChange={(e) => handleItemChange(index, 'perishability_level', e.target.value as PerishabilityLevel)}
                options={[
                  { value: 'Low', label: 'Low - Dry/canned goods' },
                  { value: 'Medium', label: 'Medium - Chilled goods' },
                  { value: 'High', label: 'High - Fresh produce/dairy' },
                ]}
              />
              <Input
                label="Recent Waste Percentage"
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={item.recent_waste_percentage || 0}
                onChange={(e) => handleItemChange(index, 'recent_waste_percentage', parseFloat(e.target.value) || 0)}
              />
            </div>
            {errors[`${index}-waste`] && (
              <p className="text-red-500 text-sm mt-2">{errors[`${index}-waste`]}</p>
            )}
          </div>

          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-3">Optional Fields</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Category"
                placeholder="e.g., Dairy"
                value={item.category || ''}
                onChange={(e) => handleItemChange(index, 'category', e.target.value)}
              />
              <Input
                label="Subcategory"
                placeholder="e.g., Milk Products"
                value={item.subcategory || ''}
                onChange={(e) => handleItemChange(index, 'subcategory', e.target.value)}
              />
              <Input
                label="Supplier Name"
                placeholder="e.g., Local Farmer"
                value={item.supplier_name || ''}
                onChange={(e) => handleItemChange(index, 'supplier_name', e.target.value)}
              />
              <Input
                label="Manual Reorder Level"
                type="number"
                min="0"
                value={item.manual_reorder_level || 0}
                onChange={(e) => handleItemChange(index, 'manual_reorder_level', parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>
        </div>
      ))}

      <Button type="button" variant="secondary" onClick={handleAddItem}>
        + Add Another Item
      </Button>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-900 text-sm">
          <strong>Score-driving fields:</strong> The following fields directly affect recommendations:
          usage value, lead time, seasonal factor, waste signal, and current stock.
        </p>
      </div>

      <Button type="submit" variant="primary" size="lg" loading={isLoading}>
        {submitLabel}
      </Button>
    </form>
  );
}
