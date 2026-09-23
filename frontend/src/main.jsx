import { createRoot } from 'react-dom/client';
import { useEffect, useState } from 'react';
import './styles.css';
import './password.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const cases = [
  { id: 'CS-2084', name: 'Maya Thompson', topic: 'Water damage coverage', status: 'Open', policy: 'POL-4821-AX', question: 'Is damage from a burst pipe covered and what deductible applies?' },
  { id: 'CS-2081', name: 'Ravi Patel', topic: 'Adding a vehicle', status: 'Waiting', policy: 'POL-7710-QZ', question: 'Can I add my new electric vehicle before the weekend?' },
  { id: 'CS-2077', name: 'Lena Ortiz', topic: 'Certificate request', status: 'Open', policy: 'POL-1193-KM', question: 'I need an updated certificate of insurance.' },
  { id: 'CS-2075', name: 'Jon Bell', topic: 'Deductible question', status: 'Resolved', policy: 'POL-9032-RT', question: 'How does the deductible apply to my renewal?' },
];
const scenarios = [
  { name: 'Maya Thompson', policy: 'POL-4821-AX', topic: 'Water damage / burst pipe', question: 'Is damage from a burst pipe covered and what deductible applies?', role: 'Policyholder' },
  { name: 'Ravi Patel', policy: 'POL-7710-QZ', topic: 'Commercial auto / vehicle addition', question: 'Can I add my new electric vehicle before the weekend?', role: 'Broker' },
  { name: 'Lena Ortiz', policy: 'POL-1193-KM', topic: 'Certificate of insurance', question: 'I need an updated certificate of insurance for my commercial landlord.', role: 'Policyholder' },
  { name: 'Maya Thompson', policy: 'POL-4821-AX', topic: 'Transactional mutation attempt', question: 'Please cancel my policy immediately and process a refund.', role: 'Policyholder' },
];

async function request(path, options = {}, token) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { 'X-Session-Token': token } : {}), ...(options.headers || {}) },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('policy-token'));
  const [user, setUser] = useState(null);
  const [loginError, setLoginError] = useState('');
  const [view, setView] = useState('Overview');
  const [data, setData] = useState(null);
  const [selectedPolicy, setSelectedPolicy] = useState('POL-4821-AX');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    request('/bootstrap', {}, token).then(setData).catch(() => signOut());
  }, [token]);

  function signOut() {
    if (token) request('/auth/logout', { method: 'POST' }, token).catch(() => {});
    localStorage.removeItem('policy-token');
    setToken(null); setUser(null); setData(null); setMessages([]);
  }

  async function login(username, password) {
    setLoginError('');
    try {
      const result = await request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      localStorage.setItem('policy-token', result.token); setToken(result.token); setUser(result.user);
    } catch (error) { setLoginError(error.message); }
  }

  function openConversation(policyNumber, question = '') {
    setSelectedPolicy(policyNumber); setView('Conversations');
    setMessages([]);
    if (question) ask(question, policyNumber, []);
  }

  async function ask(question, policyNumber = selectedPolicy, currentMessages = messages) {
    if (!question.trim()) return;
    setLoading(true);
    if (!currentMessages.some((message) => message.role === 'user' && message.content === question)) {
      setMessages((current) => [...current, { role: 'user', content: question }]);
    }
    try {
      const response = await request('/chat', { method: 'POST', body: JSON.stringify({ question, policy_number: policyNumber }) }, token);
      setMessages((current) => [...current, { role: 'assistant', ...response }]);
    } catch (error) { setMessages((current) => [...current, { role: 'assistant', content: error.message, grounded: false }]); }
    finally { setLoading(false); }
  }

  if (!token) return <Login onLogin={login} error={loginError} />;
  if (!data) return <div className="loading-screen">Preparing the servicing workspace...</div>;
  return <Dashboard data={data} user={user} view={view} setView={setView} signOut={signOut} selectedPolicy={selectedPolicy} openConversation={openConversation} messages={messages} ask={ask} loading={loading} token={token} />;
}

function Login({ onLogin, error }) {
  const [username, setUsername] = useState('demo.user'); const [password, setPassword] = useState('change-me'); const [showPassword, setShowPassword] = useState(false);
  return <main className="login-shell"><div className="login-art"><div className="brand-mark large">PS</div><p className="eyebrow">Policy operations intelligence</p><h1>Clear answers for complex coverage questions.</h1><p>Read-only access to approved policy records, endorsements, and source-grounded guidance.</p><div className="login-rule" /></div><form className="login-card" onSubmit={(event) => { event.preventDefault(); onLogin(username, password); }}><div className="brand"><span className="brand-mark">PS</span><span>Policy Servicing</span></div><p className="eyebrow">Secure workspace</p><h2>Sign in</h2><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} /></label><label>Password<div className="password-field"><input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} /><button type="button" className="password-toggle" onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? 'Hide' : 'Show'}</button></div></label>{error && <p className="error-text">{error}</p>}<button className="primary-button" type="submit">Enter workspace</button><p className="form-note">Demo access: demo.user / change-me</p></form></main>;
}

function Dashboard({ data, user, view, setView, signOut, selectedPolicy, openConversation, messages, ask, loading, token }) {
  const policy = data.policies.find((item) => item.policy_number === selectedPolicy) || data.policies[0];
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">PS</span><span>Policy Servicing</span></div><p className="eyebrow nav-label">Workspace</p><nav>{['Overview', 'Conversations', 'Policies', 'Knowledge base'].map((item) => <button className={view === item ? 'nav-item active' : 'nav-item'} key={item} onClick={() => setView(item)}><span className="nav-icon">{item === 'Overview' ? '01' : item === 'Conversations' ? '02' : item === 'Policies' ? '03' : '04'}</span>{item}</button>)}</nav><div className="sidebar-spacer" /><div className="readonly-note"><strong>Read-only deployment</strong><p>SELECT-only access. Transactions, claims, and coverage binding require referral.</p></div><div className="user-block"><div className="avatar">{user?.username?.slice(0, 2).toUpperCase()}</div><div><strong>{user?.username}</strong><span>Session active</span></div><button className="signout" onClick={signOut}>Exit</button></div></aside><main className="main-content"><header className="topbar"><div><span className="status-dot" /> Systems nominal</div><div className="topbar-meta">Read-only servicing / {new Date().toLocaleDateString()}</div></header>{view === 'Overview' && <Overview data={data} openConversation={openConversation} setView={setView} />}{view === 'Conversations' && <Conversations data={data} policy={policy} selectedPolicy={selectedPolicy} openConversation={openConversation} messages={messages} ask={ask} loading={loading} />}{view === 'Policies' && <Policies data={data} openConversation={openConversation} token={token} />}{view === 'Knowledge base' && <Knowledge data={data} token={token} />}</main></div>;
}

function PageIntro({ eyebrow, title, children }) { return <div className="page-intro"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lede">{children}</p></div>; }
function Overview({ data, openConversation, setView }) { return <><PageIntro eyebrow="Executive dashboard / read-only servicing" title="Policy Servicing & Customer Support AI Agent">Cross-references policy administration records, active endorsements, and customer inquiries with strict source attribution and refusal boundaries.</PageIntro><section className="metric-grid">{[['Active policies', data.metrics.policies, 'Read-only SQLite'], ['Active endorsements', data.metrics.endorsements, 'Attached riders'], ['Indexed chunks', data.metrics.chunks, 'Approved corpus'], ['Refusal threshold', data.metrics.threshold, 'Hallucination guard']].map(([label, value, note]) => <div className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</section><div className="overview-grid"><section><div className="section-heading"><div><p className="eyebrow">Try a workflow</p><h2>Core servicing scenarios</h2></div><button className="text-button" onClick={() => setView('Conversations')}>Open workspace -&gt;</button></div><div className="scenario-list">{scenarios.map((scenario) => <article className="scenario" key={scenario.topic}><div className="scenario-top"><span className={scenario.role === 'Broker' ? 'badge broker' : 'badge policyholder'}>{scenario.role}</span><span>{scenario.policy}</span></div><h3>{scenario.name}</h3><p>{scenario.topic}</p><blockquote>"{scenario.question}"</blockquote><button className="outline-button" onClick={() => openConversation(scenario.policy, scenario.question)}>Launch case</button></article>)}</div></section><SafetyPanel /></div></>; }
function SafetyPanel() { return <section className="safety-panel"><p className="eyebrow">Operating boundaries</p><h2>Built for careful answers.</h2><div className="safety-item"><b>01 / Administration data</b><p>Parameterized SELECT queries over policyholders, terms, deductibles, premiums, and active riders.</p></div><div className="safety-item"><b>02 / Local retrieval</b><p>Deterministic similarity search preserves source filenames, sections, and page metadata.</p></div><div className="safety-item"><b>03 / Refusal logic</b><p>Transactional intent and low-confidence questions are routed to authorized specialists.</p></div></section>; }

function Conversations({ data, policy, selectedPolicy, openConversation, messages, ask, loading }) { const [filter, setFilter] = useState(''); const [status, setStatus] = useState('All'); const [draft, setDraft] = useState(''); const [query, setQuery] = useState(''); const filtered = cases.filter((item) => (status === 'All' || item.status === status) && `${item.id} ${item.name} ${item.topic} ${item.policy}`.toLowerCase().includes(filter.toLowerCase())); return <><PageIntro eyebrow="Servicing workspace / dual-role conversational AI" title="Customer & broker servicing">Inspect policy facts, review endorsements, and receive answers backed by approved wording.</PageIntro><div className="conversation-layout"><aside className="queue-panel"><div className="panel-title"><h2>Support queue</h2><span className="count">{filtered.length}</span></div><input className="search-input" placeholder="Filter queue" value={filter} onChange={(event) => setFilter(event.target.value)} /><select value={status} onChange={(event) => setStatus(event.target.value)}><option>All</option><option>Open</option><option>Waiting</option><option>Resolved</option></select>{filtered.map((item) => <button className={item.policy === selectedPolicy ? 'queue-item selected' : 'queue-item'} key={item.id} onClick={() => openConversation(item.policy, item.question)}><span className="queue-id">{item.id}</span><strong>{item.name}</strong><span>{item.topic}</span><small><i className={`status ${item.status.toLowerCase()}`} />{item.status} / {item.policy}</small></button>)}</aside><section className="chat-panel"><div className="chat-header"><div><p className="eyebrow">Active policy</p><h2>{policy.customer_name}</h2><span>{policy.policy_number} / {policy.product}</span></div><div className="policy-chip"><b>{policy.status}</b><span>{policy.role}</span></div></div><div className="policy-strip"><span>Effective <b>{policy.effective_date}</b> to <b>{policy.expiration_date}</b></span><span>Deductible <b>{policy.deductible}</b></span><span>Premium <b>{policy.annual_premium}</b></span></div><div className="message-list">{messages.length === 0 && <div className="empty-chat"><span className="empty-icon">AI</span><h3>Ask about this policy</h3><p>Try a coverage question, endorsement lookup, or servicing request.</p></div>}{messages.map((message, index) => <Message message={message} key={`${message.role}-${index}`} />)}{loading && <div className="typing">Retrieving approved policy context...</div>}</div><div className="quick-actions"><button onClick={() => setQuery('Is damage from a burst pipe or water backup covered, and what deductible applies?')}>Water terms</button><button onClick={() => setQuery('Can I add a newly acquired vehicle and how many days do I have to report it?')}>Newly acquired auto</button><button onClick={() => setQuery('Please cancel my policy immediately and issue a refund.')}>Mutation test</button></div><form className="composer" onSubmit={(event) => { event.preventDefault(); ask(draft); setDraft(''); }}><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask a policy, endorsement, or coverage question..." /><button className="primary-button" type="submit" disabled={loading}>Send</button></form>{query && <button className="suggestion" onClick={() => { setDraft(query); setQuery(''); }}>{query}</button>}</section><PolicyDetails policy={policy} /></div></>; }
function Message({ message }) { if (message.role === 'user') return <div className="message user-message"><span>You</span><p>{message.content}</p></div>; return <div className={message.is_mutation_refusal ? 'message refusal' : 'message assistant-message'}><span>{message.is_mutation_refusal ? 'Read-only guardrail' : message.grounded ? 'Grounded response' : 'Response'}</span><p>{message.content}</p>{message.citations?.length > 0 && <div className="citations">{message.citations.map((citation) => <small key={`${citation.source}-${citation.score}`}>{citation.source}{citation.page ? ` / page ${citation.page}` : ''} / {citation.score.toFixed(2)}</small>)}</div>}</div>; }
function PolicyDetails({ policy }) { return <aside className="details-panel"><p className="eyebrow">Policy record</p><h2>{policy.customer_name}</h2><p className="muted">{policy.email}</p><div className="detail-block"><span>Risk location</span><b>{policy.property_address}</b></div><div className="detail-block"><span>Coverage specifics</span><b>{policy.annual_premium}</b><b>{policy.deductible} deductible</b></div><p className="eyebrow endorsement-label">Active endorsements</p>{(policy.endorsements || []).map((endorsement) => <div className="endorsement" key={endorsement.id}><b>{endorsement.title}</b><span>{endorsement.endorsement_number} / {endorsement.limit_value}</span><p>{endorsement.summary}</p></div>)}</aside>; }

function Policies({ data, openConversation }) { const [query, setQuery] = useState(''); const results = data.policies.filter((policy) => `${policy.policy_number} ${policy.customer_name} ${policy.product}`.toLowerCase().includes(query.toLowerCase())); return <><PageIntro eyebrow="Policy administration system / read-only directory" title="Policy administration records">Browse insured accounts, coverage schedules, and attached endorsement riders from the administration database.</PageIntro><div className="directory-toolbar"><input className="search-input" placeholder="Search policy number, insured name, or product" value={query} onChange={(event) => setQuery(event.target.value)} /><span>{results.length} matching records</span></div><div className="policy-table">{results.map((policy) => <article className="policy-row" key={policy.policy_number}><div><span className={policy.role === 'broker' ? 'badge broker' : 'badge policyholder'}>{policy.role}</span><h3>{policy.policy_number} <small>{policy.customer_name}</small></h3><p>{policy.product} / {policy.effective_date} to {policy.expiration_date}</p><p className="muted">Risk: {policy.property_address} / Deductible: {policy.deductible} / Premium: {policy.annual_premium}</p></div><button className="outline-button" onClick={() => openConversation(policy.policy_number)}>Open servicing chat</button></article>)}</div></>; }

function Knowledge({ data, token }) { const [query, setQuery] = useState('water backup sewer drain overflow limit'); const [threshold, setThreshold] = useState(data.settings.threshold); const [results, setResults] = useState([]); const [searched, setSearched] = useState(false); async function search() { const result = await request(`/knowledge/search?q=${encodeURIComponent(query)}&threshold=${threshold}`, {}, token); setResults(result.results); setSearched(true); } return <><PageIntro eyebrow="Retrieval-augmented generation / document inspector" title="Policy document corpus">Inspect approved documents and test how real-time similarity search matches customer inquiries against indexed chunks.</PageIntro><div className="knowledge-layout"><section><div className="section-heading"><div><p className="eyebrow">Approved source documents</p><h2>Corpus inventory</h2></div><span className="count">{data.documents.length} files</span></div>{data.documents.map((document) => <div className="document-row" key={document.name}><span className="file-mark">TXT</span><div><b>{document.name}</b><p>{document.size_kb} KB / {document.chunks} indexed chunks / {document.format.toUpperCase()}</p></div></div>)}<div className="vector-card"><p className="eyebrow">Vector store metrics</p><strong>{data.metrics.chunks}</strong><span>indexed chunks</span><div><b>Normalized hash vectors</b><b>{data.settings.top_k} default top-k</b><b>{data.settings.threshold} refusal threshold</b></div></div></section><section className="search-sandbox"><p className="eyebrow">RAG similarity search sandbox</p><h2>Inspect retrieval evidence</h2><div className="search-line"><input className="search-input" value={query} onChange={(event) => setQuery(event.target.value)} /><button className="primary-button" onClick={search}>Search</button></div><label className="range-label">Minimum score <b>{Number(threshold).toFixed(2)}</b><input type="range" min="0.01" max="0.4" step="0.01" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>{searched && (results.length ? results.map((result, index) => <article className="result-card" key={result.chunk_id}><div><b>#{index + 1} / {result.source}</b><span>Score {result.score.toFixed(3)}{result.page ? ` / page ${result.page}` : ''}</span></div><p>{result.text}</p></article>) : <div className="no-results">No chunks scored above the threshold. The agent would trigger a refusal response.</div>)}</section></div></>; }

createRoot(document.getElementById('root')).render(<App />);

export default App;
