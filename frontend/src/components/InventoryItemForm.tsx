import React, { useState } from 'react';
import { Input, Select, Button } from './common';
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
      custom_unit: '',
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
      // Required field validations
      if (!item.item_name || !item.item_name.trim()) {
        newErrors[`${index}-item_name`] = 'Item name is required and cannot be blank';
      }
      if (item.current_stock < 0 || isNaN(item.current_stock)) {
        newErrors[`${index}-current_stock`] = 'Current stock must be a number >= 0';
      }
      if (!item.unit || !item.unit.trim()) {
        newErrors[`${index}-unit`] = 'Unit is required and cannot be blank';
      }
      if (item.unit === 'other' && !item.custom_unit?.trim()) {
        newErrors[`${index}-custom_unit`] = 'Custom unit is required';
      }
      if (item.usage_value <= 0 || isNaN(item.usage_value)) {
        newErrors[`${index}-usage_value`] = 'Usage value must be a number > 0';
      }
      if (!item.usage_period || !['daily', 'weekly'].includes(item.usage_period)) {
        newErrors[`${index}-usage_period`] = 'Usage period must be either daily or weekly';
      }
      if (item.lead_time_days <= 0 || !Number.isInteger(item.lead_time_days) || isNaN(item.lead_time_days)) {
        newErrors[`${index}-lead_time_days`] = 'Lead time must be a whole number > 0';
      }
      if (item.price_per_unit < 0 || isNaN(item.price_per_unit)) {
        newErrors[`${index}-price_per_unit`] = 'Price per unit must be a number >= 0';
      }
      if (item.seasonal_factor < 0 || isNaN(item.seasonal_factor)) {
        newErrors[`${index}-seasonal_factor`] = 'Seasonal factor must be a number >= 0';
      }

      // Waste signal validation
      if (!item.perishability_level && !item.recent_waste_percentage) {
        newErrors[`${index}-waste`] = 'Please provide either perishability level or waste percentage';
      } else {
        // Validate perishability level if provided
        if (item.perishability_level && !['low', 'medium', 'high'].includes(item.perishability_level)) {
          newErrors[`${index}-perishability_level`] = 'Perishability level must be low, medium, or high';
        }
        // Validate waste percentage if provided
        if (item.recent_waste_percentage !== undefined && item.recent_waste_percentage !== null) {
          if (item.recent_waste_percentage < 0 || item.recent_waste_percentage > 100 || isNaN(item.recent_waste_percentage)) {
            newErrors[`${index}-recent_waste_percentage`] = 'Waste percentage must be a number between 0 and 100';
          }
        }
      }

      // Optional field validations
      if (item.manual_reorder_level !== undefined && item.manual_reorder_level !== null && (item.manual_reorder_level < 0 || isNaN(item.manual_reorder_level))) {
        newErrors[`${index}-manual_reorder_level`] = 'Manual reorder level must be a number >= 0';
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
        custom_unit: '',
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
      const finalItems: ManualItemInput[] = items.map(item => ({
        ...item,
        unit: item.unit === 'other'
          ? item.custom_unit!
          : item.unit
      }));
      onSubmit(finalItems);
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
              help="The display name for this inventory item (e.g., 'Fresh Milk'). Must be unique enough to identify it in reports."
              placeholder="e.g., Fresh Milk"
              value={item.item_name}
              onChange={(e) => handleItemChange(index, 'item_name', e.target.value)}
              error={errors[`${index}-item_name`]}
            />
            <Input
              label="Current Stock *"
              help="How much of this item you have in inventory right now, measured in the unit below. Used to compute days of cover and urgency."
              type="number"
              min="0"
              value={item.current_stock}
              onChange={(e) => handleItemChange(index, 'current_stock', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-current_stock`]}
            />
            <Select
              label="Unit *"
              value={item.unit}
              onChange={(e) => handleItemChange(index, 'unit', e.target.value)}
              error={errors[`${index}-unit`]}
              options={[
                { value: 'kg', label: 'Kilogram (kg)' },
                { value: 'g', label: 'Gram (g)' },
                { value: 'liter', label: 'Liter (L)' },
                { value: 'ml', label: 'Milliliter (ml)' },
                { value: 'pcs', label: 'Pieces (pcs)' },
                { value: 'pack', label: 'Pack' },
                { value: 'box', label: 'Box' },
                { value: 'bottle', label: 'Bottle' },
                { value: 'can', label: 'Can' },
                { value: 'tray', label: 'Tray' },
                { value: 'dozen', label: 'Dozen' },
                { value: 'other', label: 'Other (specify manually)' },
              ]}
            />
            {item.unit === 'other' && (
              <Input
                label="Custom Unit"
                placeholder="e.g., carton, bag"
                value={item.custom_unit || ''}
                onChange={(e) => handleItemChange(index, 'custom_unit', e.target.value)}
                error={errors[`${index}-custom_unit`]}
              />
            )}
            <Input
              label="Usage Value *"
              help="Typical quantity consumed per usage period (e.g., 5 liters per day). Drives demand forecasting."
              type="number"
              step="0.01"
              min="0.01"
              value={item.usage_value}
              onChange={(e) => handleItemChange(index, 'usage_value', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-usage_value`]}
            />
            <Select
              label="Usage Period *"
              help="The time window your Usage Value refers to. 'Daily' means per day; 'Weekly' means per 7 days."
              value={item.usage_period}
              onChange={(e) => handleItemChange(index, 'usage_period', e.target.value as UsagePeriod)}
              options={[
                { value: 'daily', label: 'Daily' },
                { value: 'weekly', label: 'Weekly' },
              ]}
            />
            <Input
              label="Lead Time (days) *"
              help="Number of days between placing a replenishment order and receiving it. Longer lead times increase urgency."
              type="number"
              min="1"
              step="1"
              value={item.lead_time_days}
              onChange={(e) => handleItemChange(index, 'lead_time_days', parseInt(e.target.value) || 1)}
              error={errors[`${index}-lead_time_days`]}
            />
            <Input
              label="Price per Unit *"
              help="Cost you pay per unit. Used to compute inventory value and waste cost exposure."
              type="number"
              step="0.01"
              min="0"
              value={item.price_per_unit}
              onChange={(e) => handleItemChange(index, 'price_per_unit', parseFloat(e.target.value) || 0)}
              error={errors[`${index}-price_per_unit`]}
            />
            <Select
              label="Seasonal Factor *"
              help="Multiplier applied to expected demand for seasonality. 1.0 means normal; above 1.0 means a seasonal peak; below 1.0 means a slower period."
              value={item.seasonal_factor.toFixed(1)}
              onChange={(e) => handleItemChange(index, 'seasonal_factor', parseFloat(e.target.value) || 0)}
              options={[
                { value: '0.8', label: '0.8 — lower demand' },
                { value: '1.0', label: '1.0 — normal' },
                { value: '1.1', label: '1.1 — slightly higher' },
                { value: '1.2', label: '1.2 — seasonal peak' },
                { value: '1.5', label: '1.5 — very high' },
              ]}
              error={errors[`${index}-seasonal_factor`]}
            />
          </div>

          <div className="border-t pt-4 mb-4">
            <h4 className="font-medium text-gray-900 mb-3">Waste Signal (required - provide at least one)</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Perishability Level"
                help="How quickly this item spoils. 'Low' = dry/canned, 'Medium' = chilled, 'High' = fresh produce/dairy. Drives waste risk score."
                value={item.perishability_level || ''}
                onChange={(e) => handleItemChange(index, 'perishability_level', e.target.value as PerishabilityLevel)}
                error={errors[`${index}-perishability_level`]}
                options={[
                  { value: 'low', label: 'Low - Dry/canned goods' },
                  { value: 'medium', label: 'Medium - Chilled goods' },
                  { value: 'high', label: 'High - Fresh produce/dairy' },
                ]}
              />
              <Input
                label="Recent Waste Percentage"
                help="Percentage of stock thrown away recently (0–100). Leave blank if you don't have data and use Perishability instead."
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={item.recent_waste_percentage || ''}
                onChange={(e) => handleItemChange(index, 'recent_waste_percentage', parseFloat(e.target.value) || undefined)}
                error={errors[`${index}-recent_waste_percentage`]}
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
                help="High-level grouping for reporting (e.g., Dairy, Produce, Bakery). Useful for filtering and rollups."
                placeholder="e.g., Dairy"
                value={item.category || ''}
                onChange={(e) => handleItemChange(index, 'category', e.target.value)}
              />
              <Input
                label="Subcategory"
                help="More specific grouping inside the Category (e.g., 'Milk Products' under 'Dairy')."
                placeholder="e.g., Milk Products"
                value={item.subcategory || ''}
                onChange={(e) => handleItemChange(index, 'subcategory', e.target.value)}
              />
              <Input
                label="Supplier Name"
                help="Name of the vendor you order this item from. Shown on dashboards and records."
                placeholder="e.g., Local Farmer"
                value={item.supplier_name || ''}
                onChange={(e) => handleItemChange(index, 'supplier_name', e.target.value)}
              />
              <Input
                label="Manual Reorder Level"
                help="Optional override for the reorder threshold. Leave blank to let StockWise compute it from usage and lead time."
                type="number"
                min="0"
                value={item.manual_reorder_level || ''}
                onChange={(e) => handleItemChange(index, 'manual_reorder_level', parseFloat(e.target.value) || undefined)}
                error={errors[`${index}-manual_reorder_level`]}
              />
            </div>
          </div>
        </div>
      ))}

      <Button type="button" variant="secondary" onClick={handleAddItem}>
        + Add Another Item
      </Button>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-900 text-sm mb-2">
          <strong>Required fields:</strong> All fields marked with * must be filled correctly.
        </p>
        <p className="text-blue-900 text-sm mb-2">
          <strong>Waste signal:</strong> You must provide either perishability level or recent waste percentage.
        </p>
        <p className="text-blue-900 text-sm">
          <strong>Score-driving fields:</strong> Usage value, lead time, seasonal factor, waste signal, and current stock directly affect recommendations.
        </p>
      </div>

      <Button type="submit" variant="primary" size="lg" loading={isLoading}>
        {submitLabel}
      </Button>
    </form>
  );
}
