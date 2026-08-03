import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Projects from './pages/Projects';
import Targets from './pages/Targets';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <Routes>
          <Route path="/" element={<Projects />} />
          <Route path="/projects/:projectId/targets" element={<Targets />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
