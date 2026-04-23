# Frontend Development Quick Start

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Visit http://localhost:3000

## Troubleshooting

### API Connection Issues
- Ensure backend is running on http://localhost:8000
- Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
- Check CORS settings in backend

### Port Already in Use
```bash
# Change default port
npm run dev -- -p 3001
```

### Module Not Found
```bash
rm -rf node_modules
npm install
```

## Build for Production

```bash
npm run build
npm start
```
