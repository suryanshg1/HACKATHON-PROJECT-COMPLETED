import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
// ---- 1. Import the provider ----
import { WebSocketProvider } from './contexts/WebSocketContext';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    {/* ---- 2. Wrap App with the provider ---- */}
    <WebSocketProvider>
      <App />
    </WebSocketProvider>
  </React.StrictMode>
);