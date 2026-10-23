import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/context/AuthContext';
import { FleetSocketProvider } from '@/context/FleetSocketContext';
import { AppRoutes } from '@/routes/AppRoutes';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <FleetSocketProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </FleetSocketProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
