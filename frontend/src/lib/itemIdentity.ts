import { InventoryItem } from '@/types';

export function findInventoryItemByRouteId(
  items: InventoryItem[],
  routeItemId: string | string[] | undefined
): InventoryItem | undefined {
  const itemId = Array.isArray(routeItemId) ? routeItemId[0] : routeItemId;
  if (!itemId) return undefined;

  return items.find((item) => String(item.item_id) === itemId);
}
