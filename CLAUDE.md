# GlovePost Development Guidelines

## Build & Test Commands
- Start development server: `npm run dev`
- Build for production: `npm run build` 
- Run all tests: `npm test`
- Run single test: `npm test -- -t "test name"`
- Lint code: `npm run lint`
- Format code: `npm run format`

## Code Style Guidelines
- **Stack**: React.js (front-end), Node.js (API), Python (recommendation engine)
- **Formatting**: Use Prettier with 2-space indentation
- **Naming**: camelCase for variables/functions, PascalCase for components/classes
- **Imports**: Group imports (React, third-party, local) with blank line between groups
- **Components**: Create modular components in separate files, use functional components with hooks
- **Error Handling**: Try/catch for async operations, proper error propagation to UI
- **Types**: Use TypeScript with explicit types, avoid `any` unless necessary
- **API Calls**: Use async/await pattern with proper loading/error states
- **CSS**: Use CSS modules or styled-components for component styling
- **Testing**: Write unit tests for core logic using Jest/React Testing Library