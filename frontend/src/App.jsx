import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Projects from './pages/Projects';
import Targets from './pages/Targets';
import Hosts from './pages/Hosts';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <Routes>
          <Route path="/" element={<Projects />} />
          <Route path="/projects/:projectId/targets" element={<Targets />} />
          <Route path="/targets/:targetId/hosts" element={<Hosts />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
