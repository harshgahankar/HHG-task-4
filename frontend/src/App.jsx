import { BrowserRouter, Routes, Route } from 'react-router-dom';
import CaseList from './components/CaseList';
import CaseDetail from './components/CaseDetail';
import GraphView from './components/GraphView';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>TigerGraph Fraud Investigation Agent</h1>
          <span className="subtitle">Agentic fraud investigation powered by graph analytics</span>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<CaseList />} />
            <Route path="/case/:caseId" element={<CaseDetail />} />
            <Route path="/graph/:txnId" element={<GraphView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
