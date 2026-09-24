import { BrowserRouter, Routes, Route } from 'react-router-dom';
import InvestigationView from './components/InvestigationView';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/*" element={<InvestigationView />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
