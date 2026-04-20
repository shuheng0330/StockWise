# StockWise Frontend

A modern React + Next.js frontend application for inventory analysis, stock management, and intelligent recommendations.

## Features

### 1. **Entry Page** (`/`)
- Choose between CSV upload or manual entry modes
- CSV file upload with validation
- Manual item entry with form validation
- Display CSV format requirements and example template
- Support for adding, duplicating, and removing inventory items

### 2. **Analysis Dashboard** (`/dashboard/[analysisId]`)
- KPI summary cards displaying:
  - Total items count
  - Restock Now items
  - Buy Less items
  - High waste risk items
  - Inventory value at risk
  - Average days of cover
- Ranked item recommendation table with:
  - Search by item name, category, or supplier
  - Filter by action type (RESTOCK_NOW, BUY_LESS, DELAY_PURCHASE, MONITOR_CLOSELY)
  - Display of urgency and waste risk scores with visual indicators
  - Quick access to simulation and explanation views

### 3. **Records Review & Edit Page** (`/records/[analysisId]`)
- View all inventory records in editable table
- Inline edit functionality for item details
- Delete record capability with confirmation
- Prevent deletion of final remaining item
- Auto-refresh recommendation after updates

### 4. **Simulation Page** (`/simulation/[analysisId]/[itemId]`)
- Compare current vs. simulated inventory scenarios
- Enter proposed reorder quantity
- View simulated metrics:
  - Cash outlay
  - Coverage days
  - Inventory value
  - Estimated waste cost
  - Risk change
- Visual score indicators and action recommendation
- Quick link to get explanation for simulated result

### 5. **Explanation Drawer** (`/explanation/[analysisId]/[itemId]`)
- Display AI-generated or fallback explanations
- Show explanation source (mock, live, or fallback)
- Priority level indicator
- Decision explanation with trade-off analysis
- Suggested next steps
- Confidence notes and warning flags

### 6. **Error & Empty States**
- Clear, user-friendly error messages
- Loading states for async operations
- Empty state displays
- Validation error feedback

## Tech Stack

- **Framework**: Next.js 14
- **UI Library**: React 18
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **API Client**: Axios
- **Notifications**: React Hot Toast
- **Icons**: Lucide React
- **Language**: TypeScript

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── common.tsx       # Common UI elements (Button, Input, Alert, etc.)
│   │   ├── InventoryItemForm.tsx
│   │   ├── ItemSimulation.tsx
│   │   └── ExplanationDrawer.tsx
│   ├── pages/              # Next.js pages and routes
│   │   ├── index.tsx       # Entry page
│   │   ├── dashboard/      # Dashboard
│   │   ├── records/        # Records management
│   │   ├── simulation/     # Simulation
│   │   ├── explanation/    # Explanation drawer
│   │   ├── _app.tsx        # App wrapper
│   │   ├── _document.tsx   # HTML document
│   │   └── 404.tsx         # Error page
│   ├── services/
│   │   └── api.ts          # API client with all endpoints
│   ├── store/
│   │   └── analysisStore.ts # Zustand state management
│   ├── types/
│   │   └── index.ts        # TypeScript type definitions
│   └── styles/
│       └── globals.css     # Global styles
├── public/                 # Static files
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
└── next.config.js
```

## Installation & Setup

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Production Build

```bash
npm run build
npm start
```

## API Integration

The frontend integrates with the StockWise backend API using the `apiClient` service:

### Endpoints Used

- `POST /api/v1/analyses` - Upload CSV
- `POST /api/v1/manual-analyses` - Create manual analysis
- `GET /api/v1/analyses/{analysis_id}` - Get analysis
- `GET /api/v1/analyses/{analysis_id}/records` - Get records
- `PATCH /api/v1/analyses/{analysis_id}/items/{item_id}` - Update record
- `DELETE /api/v1/analyses/{analysis_id}/items/{item_id}` - Delete record
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/simulate` - Simulate reorder
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/explanation` - Get explanation

## Component Documentation

### Common Components

#### `Button`
- Props: `variant`, `size`, `loading`, HTML button attributes
- Variants: `primary`, `secondary`, `danger`, `outline`
- Sizes: `sm`, `md`, `lg`

#### `Input`
- Props: `label`, `error`, HTML input attributes

#### `Select`
- Props: `label`, `error`, `options`, HTML select attributes

#### `Alert`
- Props: `type` (error|success|info|warning), `title`, `message`, `onClose`

#### `Card`
- Props: `children`, `className`

#### `Badge`
- Props: `label`, `variant` (success|warning|danger|info)

### Form Components

#### `InventoryItemForm`
Complete form for adding/editing inventory items with:
- Required fields: item name, stock, unit, usage, lead time, price, seasonal factor
- Waste signal validation (perishability level or waste percentage)
- Advanced fields (manual reorder level, waste percentage)
- Add, duplicate, remove item functionality

#### `ItemSimulation`
Simulation component with:
- Current state display
- Simulated quantity input
- Results comparison
- Score visualizations

#### `ExplanationDrawer`
Full-screen explanation drawer with:
- Source indicator
- Priority level
- Decision explanation
- Trade-off analysis
- Suggested actions
- Warning flags

## State Management

Using Zustand for lightweight state management:

```typescript
const { 
  currentAnalysis, 
  setCurrentAnalysis,
  currentItem,
  setCurrentItem,
  filterOptions,
  setFilterOptions
} = useAnalysisStore();
```

## Styling

The application uses Tailwind CSS with custom theme colors:
- Primary: Blue (#3B82F6)
- Secondary: Green (#10B981)
- Warning: Amber (#F59E0B)
- Danger: Red (#EF4444)

## Testing

```bash
npm run test
npm run test:watch
```

## Deployment

### Vercel

```bash
npm install -g vercel
vercel
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Error Handling

- API errors display user-friendly messages
- Loading states prevent multiple submissions
- Validation errors provide specific feedback
- Toast notifications for success/error states
- Fallback explanations if AI generation fails

## Performance Optimizations

- Image optimization with Next.js Image component (when needed)
- Code splitting and lazy loading
- Memoization of expensive components
- Efficient API calls with proper caching
- Client-side search and filtering

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Proprietary - StockWise Project
