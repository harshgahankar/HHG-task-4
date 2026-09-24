import { useState, useEffect, useCallback } from 'react';
import { fetchCases, fetchCase, runInvestigation, fetchSubgraph, fetchSimilarCases, fetchGraphStats } from '../api';
import Header from './Header';
import TelemetryRibbon from './TelemetryRibbon';
import LeftColumn from './LeftColumn';
import MiddleColumn from './MiddleColumn';
import RightColumn from './RightColumn';
import BottomWorkspace from './BottomWorkspace';

export default function InvestigationView() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [similarCases, setSimilarCases] = useState([]);
  const [subgraph, setSubgraph] = useState(null);
  const [graphStats, setGraphStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [simResponse, setSimResponse] = useState(null);
  const [activeTab, setActiveTab] = useState('graph');
  const [toast, setToast] = useState(null);
  const [frozen, setFrozen] = useState(false);

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  useEffect(() => {
    fetchCases().then(d => {
      setCases(d.cases);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const selectCase = async (caseId) => {
    setSelectedCase(caseId);
    setSimResponse(null);
    setActiveTab('graph');
    try {
      const [d, s] = await Promise.all([
        fetchCase(caseId),
        fetchSimilarCases(caseId).catch(() => ({ similar_cases: [] }))
      ]);
      setCaseData(d);
      setSimilarCases(s.similar_cases || []);
      const txnId = d?.case?.affected_txn_ids?.[0] || '';
      if (txnId) {
        fetchSubgraph(txnId, 2).then(setSubgraph).catch(() => {});
      }
    } catch {}
  };

  const investigate = async (caseId) => {
    if (!caseId) return;
    setInvestigating(true);
    showToast('Investigation streaming started...', 'info');
    try {
      const d = await runInvestigation(caseId);
      setCaseData(d);
      const txnId = d?.case?.affected_txn_ids?.[0] || '';
      if (txnId) {
        fetchSubgraph(txnId, 2).then(setSubgraph).catch(() => {});
      }
      showToast('Investigation complete', 'success');
    } catch (e) {
      showToast('Investigation failed: ' + e.message, 'error');
    }
    setInvestigating(false);
  };

  const handleSimulate = (type) => {
    if (!caseData?.case) return;
    setSimResponse(type);
    const prob = type === 'denied' ? Math.min(0.95, (caseData.case.fraud_probability || 0.5) + 0.3) :
                 type === 'approved' ? Math.max(0.1, (caseData.case.fraud_probability || 0.5) - 0.4) :
                 caseData.case.fraud_probability || 0.5;
    setCaseData(prev => ({
      ...prev,
      case: { ...prev.case, fraud_probability: prob },
    }));
    const msg = type === 'denied' ? 'Customer denied transaction — CONFIRMED FRAUD' :
                type === 'approved' ? 'Customer confirmed — LOW RISK' :
                'Timeout — escalating to fallback';
    showToast(msg, type === 'denied' ? 'error' : type === 'approved' ? 'success' : 'warning');
  };

  const handleApprove = () => {
    if (!selectedCase) return;
    setCaseData(prev => ({
      ...prev,
      case: { ...prev.case, status: 'approved', verdict: prev?.case?.verdict || 'legitimate' },
    }));
    showToast('Recommendation approved & confirmed', 'success');
  };

  const handleExportSAR = () => {
    if (!caseData) {
      showToast('No case selected — select a case first', 'warning');
      return;
    }
    const sar = caseData.sar;
    if (!sar?.file) {
      showToast('SAR not required for this case', 'info');
      return;
    }
    const blob = new Blob([JSON.stringify(sar, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SAR-${caseData.case_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`SAR draft exported: ${caseData.case_id}`, 'success');
  };

  const handleEmergencyFreeze = () => {
    if (!caseData) {
      showToast('No case selected', 'warning');
      return;
    }
    setFrozen(f => !f);
    setCaseData(prev => ({
      ...prev,
      case: { ...prev.case, status: frozen ? 'active' : 'frozen' },
    }));
    showToast(frozen ? 'Emergency freeze lifted' : 'EMERGENCY FREEZE ACTIVATED — account locked', frozen ? 'info' : 'error');
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space' && !investigating) {
        e.preventDefault();
        if (selectedCase) investigate(selectedCase);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedCase, investigating]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--outline)' }}>
        <span className="material-symbols-outlined animate-spin" style={{ marginRight: 8 }}>refresh</span>
        Loading fraud investigation agent...
      </div>
    );
  }

  const c = caseData?.case || {};
  const nba = caseData?.next_best_actions || {};
  const sar = caseData?.sar || {};
  const evidence = caseData?.evidence_requests || [];
  const evidenceList = c.evidence || [];

  return (
    <>
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
            {toast.type === 'error' ? 'error' : toast.type === 'success' ? 'check_circle' : toast.type === 'warning' ? 'warning' : 'info'}
          </span>
          {toast.msg}
        </div>
      )}
      <Header
        caseData={caseData}
        investigating={investigating}
        onReRun={() => investigate(selectedCase)}
        onExportSAR={handleExportSAR}
        onEmergencyFreeze={handleEmergencyFreeze}
      />
      <TelemetryRibbon caseData={caseData} graphStats={graphStats} />
      <div className="app-main">
        <div className="grid-3col">
          <div>
            <LeftColumn
              cases={cases}
              selectedCase={selectedCase}
              caseData={caseData}
              onSelectCase={selectCase}
            />
          </div>
          <div>
            <MiddleColumn
              caseData={caseData}
              investigating={investigating}
              simResponse={simResponse}
              onSimulate={handleSimulate}
            />
          </div>
          <div>
            <RightColumn
              caseData={caseData}
              nba={nba}
              onApprove={handleApprove}
              frozen={frozen}
            />
          </div>
        </div>
        <BottomWorkspace
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          subgraph={subgraph}
          caseData={caseData}
          evidenceList={evidenceList}
          similarCases={similarCases}
          sar={sar}
          nba={nba}
        />
      </div>
    </>
  );
}
