import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage.jsx';
import { ThemePage } from './pages/ThemePage.jsx';
import { RoomPage } from './pages/RoomPage.jsx';
import { SettingsPage } from './pages/SettingsPage.jsx';
import { SpotifyCallback } from './auth/SpotifyCallback.jsx';
import { NavBar } from './components/NavBar.jsx';
import { UpdatePrompt } from './components/UpdatePrompt.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <div className="max-w-md mx-auto min-h-screen">
        <UpdatePrompt />
        <Routes>
          <Route path="/"         element={<HomePage />} />
          <Route path="/theme"    element={<ThemePage />} />
          <Route path="/room"     element={<RoomPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/callback" element={<SpotifyCallback />} />
        </Routes>
        <NavBar />
      </div>
    </BrowserRouter>
  );
}
