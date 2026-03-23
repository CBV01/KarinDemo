import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { useLocation, useNavigate, Routes, Route } from 'react-router-dom';
import {
   Home,
   Users,
   MoreHorizontal,
   Plus,
   ClipboardList,
   History,
   Smartphone,
   Target,
   Zap,
   PhoneCall,
   Building,
   DollarSign,
   TrendingUp,
   Globe,
   Activity,
   Search,
   Bell,
   ShieldCheck,
   Mail,
   CheckCircle2,
   Clock,
   ArrowRight,
   Send,
   Sliders,
   Calendar,
   Settings,
   X,
   FileText,
   Link,
   Calculator,
   Upload
} from 'lucide-react';
import {
   XAxis,
   YAxis,
   CartesianGrid,
   Tooltip,
   ResponsiveContainer,
   AreaChart,
   Area
} from 'recharts';
import api from './api';

const chartData = [
   { name: 'Mon', in: 40, out: 24 }, { name: 'Tue', in: 32, out: 13 }, { name: 'Wed', in: 56, out: 98 },
   { name: 'Thu', in: 45, out: 39 }, { name: 'Fri', in: 78, out: 48 }, { name: 'Sat', in: 65, out: 38 }, { name: 'Sun', in: 90, out: 43 },
];

const App = () => {
   const location = useLocation();
   const navigate = useNavigate();
   
   // Derive activeTab from URL. Pathname usually starts with a slash like "/leads"
   const activeTab = location.pathname.split('/').filter(Boolean)[0] || 'dashboard';
   
   const [anniversaries, setAnniversaries] = useState<any[]>([]);
   const [leads, setLeads] = useState<any[]>([]);
   const [clients, setClients] = useState<any[]>([]);
   const [interactions, setInteractions] = useState<any[]>([]);
   const [briefingMsg, setBriefingMsg] = useState('Syncing command pulse...');
   const [googleConnected, setGoogleConnected] = useState(false);
   const [loading, setLoading] = useState(true);
   const [toast, setToast] = useState<{ message: string, type: 'success' | 'info' } | null>(null);
   const [activeModal, setActiveModal] = useState<string | null>(null);
   const [modalTab, setModalTab] = useState<'MANUAL' | 'IMPORT'>('MANUAL');
   const [formData, setFormData] = useState<any>({});
   const [emailTemplate, setEmailTemplate] = useState("Hi [Name],\n\nKarin was just reviewing your 2-year settlement anniversary at [Address]. Rodney market data shows a strong upward drift since [Date].\n\nWould you be open to seeing the fresh valuation report my AI engine just drafted for you?");
   const [smsTemplate, setSmsTemplate] = useState("Hi [Name], check your email for the [Address] market update I just sent! Let Karin know if you want the full physical appraisal? - Karin's AI Assistant");

   const handleRewrite = async (type: 'email' | 'sms') => {
      const content = type === 'email' ? emailTemplate : smsTemplate;
      const originalText = type === 'email' ? 'Regenerating Email...' : 'Refining SMS...';
      showToast(originalText, 'info');
      
      try {
         const res = await api.post('/assistant/rewrite', { content, tone: 'professional' });
         if (type === 'email') setEmailTemplate(res.data.content);
         else setSmsTemplate(res.data.content);
         showToast('AI optimization complete.', 'success');
      } catch (err) {
         showToast('AI rewrite failed. Check connection.', 'info');
      }
   };

   const handleLaunchCampaign = async (type: 'email' | 'sms') => {
      const content = type === 'email' ? emailTemplate : smsTemplate;
      showToast(`Launching ${type} campaign...`, 'info');
      try {
         const res = await api.post('/campaigns/launch', { 
            campaign_id: 'manual-trigger', 
            template_type: type, 
            content 
         });
         showToast(res.data.message, 'success');
      } catch (err) {
         showToast('Campaign launch failed.', 'info');
      }
   };

   const showToast = (message: string, type: 'success' | 'info' = 'success') => {
      setToast({ message, type });
      setTimeout(() => setToast(null), 3000);
   };

   const closeModals = () => setActiveModal(null);

   const stats = [
      { label: 'Active Pipeline', val: leads.length, inc: '+2', icon: PhoneCall, theme: 'indigo' },
      { label: 'Outbound Wave', val: '48', inc: 'Vapi Active', icon: Target, theme: 'emerald' },
      { label: 'Anniversaries', val: anniversaries.length, inc: 'Detection', icon: Building, theme: 'amber' },
      { label: 'Client Base', val: clients.length, inc: '+4%', icon: Activity, theme: 'rose' },
   ];

   const fetchData = async () => {
      setLoading(true);
      try {
         const [briefRes, annivRes, leadsRes, clientsRes, intRes, googleRes] = await Promise.all([
            api.get('/assistant/morning-briefing'),
            api.get('/check-anniversaries'),
            api.get('/leads'),
            api.get('/clients'),
            api.get('/interactions'),
            api.get('/auth/status')
         ]);
         setBriefingMsg(briefRes.data.content);
         setAnniversaries(annivRes.data.today_anniversaries);
         setLeads(leadsRes.data);
         setClients(clientsRes.data);
         setInteractions(intRes.data);
         setGoogleConnected(googleRes.data.connected);
      } catch (err) {
         console.error("Error fetching data:", err);
      } finally {
         setLoading(false);
      }
   };

   const handleConnectGoogle = async () => {
      try {
         const res = await api.get('/auth/login');
         window.location.href = res.data.url;
      } catch (err) {
         showToast('Failed to trigger Google Handshake.', 'info');
      }
   };

   useEffect(() => {
      fetchData();
      // Check for success URL params
      const params = new URLSearchParams(window.location.search);
      if (params.get('auth') === 'success') {
         showToast('Google Handshake Successful!', 'success');
         // Clean up URL
         window.history.replaceState({}, document.title, window.location.pathname);
      }
   }, []);

   const handleExecuteProtocol = async () => {
      try {
         if (activeModal === 'RECORD_LEAD' && modalTab === 'MANUAL') {
            await api.post('/leads', {
               name: formData.name,
               phone: formData.phone,
               email: formData.email,
               property_address: formData.address,
               purchase_date: formData.purchase_date,
               intent: 'seller',
               source: 'Manual Entry'
            });
            showToast('Lead entry successfully stabilized in the matrix.');
         } else if (activeModal === 'BOOK_APPRAISAL') {
            await api.post('/appraisals/book', {
               address: formData.address,
               appointment_time: formData.time,
               client_id: 'internal'
            });
            showToast('Physical appraisal booking synced to nodes.');
         }
         
         await fetchData(); // Refresh data
         closeModals();
         setFormData({});
      } catch (err) {
         showToast('Protocol failure detected in the handshake.', 'info');
      }
   };

   const handleImport = async (e: any) => {
      const file = e.target.files[0];
      if (!file) return;
      
      showToast('Initializing Real-time Parser...', 'info');
      
      Papa.parse(file, {
         header: true,
         skipEmptyLines: true,
         complete: async (results) => {
            const dataToImport = results.data.map((row: any) => ({
               name: row.full_name || row.name || row.Name || row['Full Name'],
               email: row.email || row.Email || '',
               phone: row.phone || row.Phone || row['Phone Number'] || '',
               address: row.address || row.Address || row.property_address || ''
            })).filter(r => r.name); // Final validation check

            if (dataToImport.length === 0) {
               showToast('Parsing failed: No valid nodes identified.', 'info');
               return;
            }

            try {
               await api.post('/bulk-import', dataToImport);
               showToast(`Success: ${dataToImport.length} nodes added to matrix.`);
               await fetchData();
               closeModals();
            } catch (err) {
               showToast('Internal Server Error during handshake.', 'info');
            }
         },
         error: () => {
            showToast('Protocol failure: File parsing error.', 'info');
         }
      });
   };

   const renderDashboard = () => (
      <div className="space-y-4 max-w-full animate-in fade-in duration-500 pb-12">
         <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((stat, i) => (
               <div key={i} className={`premium-card p-5 h-32 border border-slate-100 bg-white shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 cursor-default flex flex-col justify-between overflow-hidden relative group border-l-4 ${
                  stat.theme === 'indigo' ? 'border-l-indigo-500 hover:border-indigo-200' :
                  stat.theme === 'emerald' ? 'border-l-emerald-500 hover:border-emerald-200' :
                  stat.theme === 'amber' ? 'border-l-amber-500 hover:border-amber-200' :
                  'border-l-rose-500 hover:border-rose-200'
               }`}>
                  <div className="flex items-center justify-between relative z-10">
                     <div className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-500 shadow-sm ${
                        stat.theme === 'indigo' ? 'bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white group-hover:shadow-indigo-200' :
                        stat.theme === 'emerald' ? 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white group-hover:shadow-emerald-200' :
                        stat.theme === 'amber' ? 'bg-amber-50 text-amber-600 group-hover:bg-amber-600 group-hover:text-white group-hover:shadow-amber-200' :
                        'bg-rose-50 text-rose-600 group-hover:bg-rose-600 group-hover:text-white group-hover:shadow-rose-200'
                     }`}>
                        <stat.icon size={18} strokeWidth={2.5} />
                     </div>
                     <span className={`text-[10px] font-black px-2.5 py-1 rounded-full border uppercase tracking-tighter shadow-sm transition-colors ${
                        stat.theme === 'indigo' ? 'bg-indigo-50/50 text-indigo-600 border-indigo-100' :
                        stat.theme === 'emerald' ? 'bg-emerald-50/50 text-emerald-600 border-emerald-100' :
                        stat.theme === 'amber' ? 'bg-amber-50/50 text-amber-600 border-amber-100' :
                        'bg-rose-50/50 text-rose-600 border-rose-100'
                     }`}>{stat.inc}</span>
                  </div>
                  <div className="relative z-10">
                     <p className="text-slate-400 font-bold text-[10px] uppercase tracking-[0.2em] mb-1.5 opacity-80 group-hover:opacity-100 transition-opacity">{stat.label}</p>
                     <h3 className="text-2xl font-black text-slate-800 tracking-tighter leading-none group-hover:scale-105 transition-transform origin-left">{stat.val}</h3>
                  </div>
                  
                  {/* Modern Glassmorphism Accent Blur */}
                  <div className={`absolute -right-4 -bottom-4 w-24 h-24 rounded-full blur-3xl opacity-0 group-hover:opacity-20 transition-opacity duration-700 ${
                     stat.theme === 'indigo' ? 'bg-indigo-600' :
                     stat.theme === 'emerald' ? 'bg-emerald-600' :
                     stat.theme === 'amber' ? 'bg-amber-600' :
                     'bg-rose-600'
                  }`}></div>
               </div>
            ))}
         </section>

         <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 premium-card p-8 min-h-[400px] flex flex-col bg-white border border-slate-100 shadow-[0_4px_20px_rgba(0,0,0,0.03)] selection:bg-indigo-50">
               <div className="flex items-center justify-between mb-8 px-1">
                  <div>
                     <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest leading-none mb-1.5 flex items-center gap-2 underline decoration-indigo-200/50 decoration-2 underline-offset-4">System Velocity</h3>
                     <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5 opacity-60">Real-time Command Hub Dynamics</p>
                  </div>
                  <div className="flex bg-slate-50 p-1 rounded-xl border border-slate-100">
                     <button className="px-5 py-1.5 bg-white text-indigo-600 font-bold text-[9px] uppercase tracking-[0.2em] rounded-lg shadow-sm">Real-Time</button>
                     <button className="px-5 py-1.5 text-slate-400 font-bold text-[9px] uppercase tracking-[0.2em] hover:text-indigo-600 transition-colors">7-Day Matrix</button>
                  </div>
               </div>
               <div className="flex-1 w-full -ml-8">
                  <ResponsiveContainer width="105%" height="100%">
                     <AreaChart data={chartData}>
                        <defs>
                           <linearGradient id="p-grad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#6366F1" stopOpacity={0.15} />
                              <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                           </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F8FAFC" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em' }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }} />
                        <Tooltip cursor={{ stroke: '#EEF2FF', strokeWidth: 2 }} contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', padding: '12px' }} />
                        <Area type="monotone" dataKey="in" stroke="#6366F1" strokeWidth={3} fillOpacity={1} fill="url(#p-grad)" animationDuration={1000} />
                     </AreaChart>
                  </ResponsiveContainer>
               </div>
            </div>

            <div className="premium-card p-0 flex flex-col relative overflow-hidden bg-white border border-slate-100 shadow-[0_4px_20px_rgba(0,0,0,0.03)] group transition-all hover:border-indigo-200">
               <div className="p-8 pb-4 border-b border-slate-50 flex items-center justify-between">
                  <div>
                     <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest leading-none mb-1.5">Strategic Briefing</h3>
                     <p className="text-[10px] text-indigo-500 font-bold uppercase tracking-widest opacity-80 flex items-center gap-2 tracking-[0.2em]">
                        <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-ping"></span> Sync Active
                     </p>
                  </div>
                  <div className="w-11 h-11 bg-slate-900 rounded-2xl flex items-center justify-center text-indigo-400 shadow-xl shadow-slate-200 group-hover:scale-110 group-hover:bg-indigo-600 group-hover:text-white transition-all"><Smartphone size={20} strokeWidth={2.5} /></div>
               </div>
               <div className="flex-1 p-8 pt-6 space-y-6 relative z-10 no-scrollbar overflow-y-auto">
                  <div className="italic text-[13px] text-slate-500 font-medium leading-[2.1] whitespace-pre-wrap border-l-4 border-indigo-100 pl-6 py-2 bg-slate-50/30 rounded-r-2xl">
                     "{briefingMsg}"
                  </div>
                  <div className="flex items-center gap-3 text-[9px] font-bold text-slate-400 uppercase tracking-[0.15em] bg-slate-50 p-4 rounded-2xl border border-slate-100 mt-4 group-hover:border-indigo-100/50 transition-colors">
                     <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_12px_rgba(16,185,129,0.5)]"></div>
                     WhatsApp Hub Listener • [45] Active Nodes
                  </div>
               </div>
               {/* Abstract Background Decoration */}
               <div className="absolute right-0 bottom-0 p-4 opacity-[0.03] -rotate-12 translate-x-6 translate-y-6 pointer-events-none">
                  <Globe size={180} />
               </div>
            </div>
         </div>

         <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="premium-card flex flex-col h-[400px] border border-slate-100 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.02)] overflow-hidden">
               <div className="p-5 border-b border-slate-50 flex items-center justify-between">
                  <div>
                     <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-[0.2em] leading-none mb-1">Communication Records</h3>
                     <p className="text-[9px] text-slate-400 font-bold uppercase tracking-tight">Active Signal Pipeline</p>
                  </div>
                  <History size={16} className="text-indigo-600 opacity-60" />
               </div>
               <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-slate-50/50">
                  {leads.length > 0 ? leads.slice(0, 8).map((lead, i) => (
                     <div key={i} className="p-4 flex items-center gap-4 hover:bg-slate-50/80 transition cursor-pointer group">
                        <div className="w-10 h-10 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-center font-bold text-slate-400 text-xs uppercase shadow-inner group-hover:bg-indigo-600 group-hover:text-white transition-all transform group-hover:scale-105">{lead.name[0]}</div>
                        <div className="flex-1 min-w-0">
                           <p className="font-bold text-slate-800 text-[13px] tracking-tight truncate">{lead.name}</p>
                           <div className="flex items-center gap-2 text-slate-400 font-bold text-[9px] uppercase tracking-tight truncate"><Building size={10} className="text-indigo-400" /> {lead.property_address || 'Identifying Asset Node...'}</div>
                        </div>
                        <div className="flex gap-1.5 opacity-40 group-hover:opacity-100 transition-opacity">
                           <div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div>
                           <div className="w-1.5 h-1.5 rounded-full bg-indigo-200"></div>
                           <div className="w-1.5 h-1.5 rounded-full bg-slate-100"></div>
                        </div>
                     </div>
                  )) : (
                     <div className="h-full flex flex-col items-center justify-center p-8 text-center opacity-40">
                        <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mb-4 border border-slate-100"><Users size={20} className="text-slate-300" /></div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No Active Records</p>
                        <p className="text-[9px] text-slate-300 font-medium max-w-[140px] mt-1 leading-relaxed">System is awaiting new inbound communication pulses.</p>
                     </div>
                  )}
               </div>
               <div className="p-4 bg-slate-50/30 border-t border-slate-50">
                  <button onClick={() => navigate('/leads')} className="w-full py-2 bg-white border border-slate-100 text-slate-400 font-bold text-[9px] uppercase tracking-widest rounded-lg hover:text-indigo-600 hover:border-indigo-100 transition-all">Expand Pipeline Stream</button>
               </div>
            </div>

            <div className="premium-card flex flex-col h-[400px] border border-slate-100 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.02)] overflow-hidden">
               <div className="p-5 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
                  <div>
                     <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-[0.2em] leading-none mb-1">Remote Interaction Log</h3>
                     <p className="text-[9px] text-emerald-600 font-bold uppercase tracking-tight">Encryption Mode: SECURE</p>
                  </div>
                  <ShieldCheck size={16} className="text-emerald-500 opacity-60" />
               </div>
               <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
                  {interactions.length > 0 ? interactions.slice(0, 6).map((log, i) => (
                     <div key={i} className="flex gap-4 relative group">
                        {i < interactions.length - 1 && <div className="absolute left-[3.5px] top-6 w-[1px] h-10 bg-slate-100 group-hover:bg-indigo-100 transition-colors"></div>}
                        <div className={`w-2 h-2 rounded-full mt-2 shrink-0 z-10 ${log.direction === 'inbound' ? 'bg-indigo-600 shadow-[0_0_8px_rgba(79,70,229,0.4)]' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]'}`}></div>
                        <div className="flex-1 min-w-0 bg-slate-50/50 p-4 rounded-2xl border border-transparent group-hover:border-slate-100 group-hover:bg-white transition-all">
                           <p className="text-slate-600 font-medium text-[12px] leading-relaxed mb-2 line-clamp-2">"{log.content}"</p>
                           <div className="flex items-center justify-between">
                              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">{log.channel} • {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              <span className={`text-[8px] font-bold px-2 py-0.5 rounded-full uppercase tracking-tighter ${log.direction === 'inbound' ? 'bg-indigo-50 text-indigo-600' : 'bg-emerald-50 text-emerald-600'}`}>{log.direction}</span>
                           </div>
                        </div>
                     </div>
                  )) : (
                     <div className="h-full flex flex-col items-center justify-center p-8 text-center opacity-40">
                        <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mb-4 border border-slate-100"><History size={20} className="text-slate-300" /></div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No Interactions Logged</p>
                        <p className="text-[9px] text-slate-300 font-medium max-w-[140px] mt-1 leading-relaxed">Waiting for data handshakes between nodes.</p>
                     </div>
                  )}
               </div>
            </div>
         </section>
      </div>
   );

   const renderLeads = () => (
      <div className="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-300 pb-12">
         <div className="flex items-center justify-between px-2">
            <div>
               <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Active Lead Pipeline</h2>
               <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Automated Qualifying Sequence (📩 ➔ 💬 ➔ 📞)</p>
            </div>
            <button
               onClick={() => setActiveModal('RECORD_LEAD')}
               className="btn-premium px-5 py-2.5">
               <Plus size={14} strokeWidth={3} /> Record Entry / Import
            </button>
         </div>
         <div className="premium-card overflow-hidden">
            <table className="premium-table w-full text-left border-collapse">
               <thead>
                  <tr className="bg-slate-50/50">
                     <th className="pl-8 py-4">Current Prospect</th>
                     <th>Asset Target</th>
                     <th>Sequence Progress</th>
                     <th>Financial Profile</th>
                     <th className="pr-8"></th>
                  </tr>
               </thead>
               <tbody>
                  {leads.map((lead, i) => (
                     <tr key={i} className="hover:bg-slate-50/40 border-b border-slate-50 transition-colors group">
                        <td className="pl-8 py-5">
                           <p className="font-bold text-slate-800 text-[14px] leading-none mb-1.5">{lead.name}</p>
                           <div className="flex flex-col gap-1">
                              <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2"><Globe size={11} className="text-indigo-600/50" /> {lead.source} • Inbound Stream</p>
                              <div className="flex items-center gap-3">
                                 {lead.email && <span className="text-[9px] font-bold text-slate-500 lowercase flex items-center gap-1"><Mail size={10} /> {lead.email}</span>}
                                 {lead.phone && <span className="text-[9px] font-bold text-slate-500 flex items-center gap-1"><Smartphone size={10} /> {lead.phone}</span>}
                              </div>
                           </div>
                        </td>
                        <td>
                           <p className="text-xs font-semibold text-slate-600 flex items-center gap-2"><Building size={14} className="text-slate-300" /> {lead.property_address || 'Address Discovery Active'}</p>
                        </td>
                        <td>
                           <div className="flex items-center gap-3">
                              <div className="flex items-center gap-1.5 grayscale opacity-50 group-hover:grayscale-0 group-hover:opacity-100 transition-all">
                                 <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${lead.status === 'active' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' : 'bg-slate-100 text-slate-300'}`}><Mail size={12} /></div>
                                 <div className={`w-3 h-0.5 rounded-full ${lead.status === 'active' ? 'bg-indigo-600' : 'bg-slate-100'}`}></div>
                                 <div className="w-7 h-7 rounded-lg bg-slate-50 text-slate-300 flex items-center justify-center border border-slate-100"><Zap size={12} /></div>
                                 <div className="w-3 h-0.5 rounded-full bg-slate-100"></div>
                                 <div className="w-7 h-7 rounded-lg bg-slate-50 text-slate-300 flex items-center justify-center border border-slate-100"><PhoneCall size={12} /></div>
                              </div>
                              <span className="text-[9px] font-bold text-slate-300 uppercase leading-none mt-1 ml-2">{lead.timeline || 'Immediate'}</span>
                           </div>
                        </td>
                        <td>
                           <div className="flex flex-col">
                              <p className="font-bold text-slate-800 text-[13px] flex items-center gap-1 mb-1"><DollarSign size={13} className="text-emerald-500" /> {lead.budget || 'Not Profiled'}</p>
                              <span className="text-[9px] font-bold text-indigo-400 uppercase leading-none">Intent: {lead.intent}</span>
                           </div>
                        </td>
                        <td className="pr-8 text-right opacity-0 group-hover:opacity-100 transition-all"><button className="p-2 text-slate-300 hover:text-indigo-600 hover:bg-white rounded-lg shadow-sm border border-slate-50"><MoreHorizontal size={18} /></button></td>
                     </tr>
                  ))}
               </tbody>
            </table>
         </div>
      </div>
   );

   const renderClients = () => (
      <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300 pb-12">
         <div className="flex items-center justify-between px-2">
            <div>
               <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Portfolio Management</h2>
               <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Central Database of Client Portfolio</p>
            </div>
            <div className="flex items-center gap-3">
               <button
                  onClick={() => { setActiveModal('RECORD_LEAD'); setModalTab('IMPORT'); }}
                  className="px-5 py-2.5 bg-white border border-slate-100 text-slate-800 text-[11px] font-bold uppercase tracking-widest rounded-xl hover:bg-slate-50 flex items-center gap-2 shadow-sm">
                  <Upload size={14} /> Database Import
               </button>
               <button
                  onClick={() => { setActiveModal('RECORD_LEAD'); setModalTab('MANUAL'); }}
                  className="btn-premium px-6"><Plus size={16} /> Record Entry
               </button>
            </div>
         </div>
         <div className="premium-card overflow-hidden">
            <table className="premium-table w-full text-left">
               <thead><tr className="bg-slate-50/50"><th className="pl-8 py-4">Portfolio Identification</th><th>Channel Details</th><th className="pr-10 text-right">Settings</th></tr></thead>
               <tbody>
                  {clients.map((client, i) => (
                     <tr key={i} className="hover:bg-slate-50/40 border-b border-slate-50 transition-colors">
                        <td className="font-bold text-slate-800 pl-8 py-6 text-sm flex items-center gap-4">
                           <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 text-xs font-bold uppercase">{client.full_name[0]}</div>
                           {client.full_name}
                        </td>
                        <td><div className="flex items-center gap-4"><div className="flex items-center gap-2"><Mail size={12} className="text-indigo-600/40" /><span className="text-xs font-semibold text-slate-600">{client.email}</span></div><div className="flex items-center gap-2 border-l border-slate-100 pl-4"><Smartphone size={12} className="text-emerald-500/40" /><span className="text-xs font-semibold text-slate-600">{client.phone}</span></div></div></td>
                        <td className="pr-10 text-right"><button className="p-2 text-slate-300 hover:text-indigo-600 hover:bg-white rounded-lg shadow-sm border border-slate-50"><MoreHorizontal size={18} /></button></td>
                     </tr>
                  ))}
               </tbody>
            </table>
         </div>
      </div>
   );

   const renderAnniversaries = () => {
      const today = new Date();
      const currentMonth = today.getMonth();
      const currentYear = today.getFullYear();
      const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
      const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay(); // 0 for Sunday, 1 for Monday

      // Adjust firstDayOfMonth to be 0 for Monday
      const startDayOffset = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;

      const calendarDays: (number | null)[] = Array.from({ length: startDayOffset }, () => null); // Empty days before 1st
      for (let i = 1; i <= daysInMonth; i++) {
         calendarDays.push(i);
      }

      const getAnniversaryDetails = (day: number) => {
         const matchingAnniversaries = anniversaries.filter(anniv => {
            const annivDate = new Date(anniv.anniversary_date);
            return annivDate.getMonth() === currentMonth && annivDate.getDate() === day;
         });
         return matchingAnniversaries;
      };

      return (
         <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300 pb-12">
            <div className="flex items-center justify-between px-2">
               <div>
                  <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Asset Persistence Matrix</h2>
                  <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Automated cycle detection: Year 1, 2, 5, 10</p>
               </div>
               <button
                  onClick={() => showToast('Proprietary matrix sync active. Scanning 500+ ownership nodes...')}
                  className="btn-premium px-8 rounded-lg flex items-center gap-3">
                  <Zap size={14} strokeWidth={3} /> Rescan Market Nodes
               </button>
            </div>

            {/* Detailed Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
               <div className="premium-card p-5 bg-white space-y-2">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Loops</p>
                  <h4 className="text-xl font-semibold text-slate-800 tracking-tight">{anniversaries.length} Owners identified</h4>
                  <div className="h-1 w-full bg-slate-50 rounded-full overflow-hidden mt-2"><div className="h-full w-2/3 bg-indigo-500 rounded-full"></div></div>
               </div>
               <div className="premium-card p-5 bg-white space-y-2">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Potential Appraisals</p>
                  <h4 className="text-xl font-semibold text-slate-800 tracking-tight">14 Projected for Apr 24</h4>
               </div>
               <div className="premium-card p-5 border-indigo-600 bg-indigo-600/5 space-y-2">
                  <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest leading-none">AI Insight</p>
                  <p className="text-[11px] font-medium text-slate-600 leading-relaxed italic">"Owners at the 2-year mark in Silverdale are showing 22% higher listing intent this cycle."</p>
               </div>
            </div>

            <div className="premium-card p-1 bg-white shadow-sm ring-1 ring-slate-100 overflow-hidden">
               <div className="grid grid-cols-7 gap-px bg-slate-100">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (<div key={d} className="bg-white p-3 text-center text-[10px] font-bold uppercase text-slate-300 tracking-[0.2em]">{d}</div>))}
                  {calendarDays.map((day, i) => {
                     const isToday = day === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear();
                     const dayAnniversaries = day ? getAnniversaryDetails(day) : [];
                     return (
                        <div key={i} className={`bg-white h-24 p-3 transition-all hover:bg-slate-50 relative group ${isToday ? 'bg-indigo-50/20' : ''}`}>
                           {day && <span className={`text-[11px] font-bold ${isToday ? 'text-indigo-600' : 'text-slate-300'}`}>{day}</span>}
                           {dayAnniversaries.length > 0 && (
                              <div className="mt-2 space-y-1">
                                 {dayAnniversaries.map((anniv, idx) => (
                                    <div key={idx} className="p-1 px-2 bg-rose-50 border border-rose-100/50 rounded-md text-[8px] font-bold text-rose-600 uppercase truncate">
                                       {anniv.address}
                                    </div>
                                 ))}
                                 <div className="p-1 px-2 bg-indigo-50 border border-indigo-100/30 rounded-md text-[8px] font-bold text-indigo-600 uppercase tracking-tighter">
                                    CYC-Yr {dayAnniversaries[0].tenure_years || 'N/A'} Match
                                 </div>
                              </div>
                           )}
                        </div>
                     );
                  })}
               </div>
            </div>

            {/* Ownership Table */}
            <div className="premium-card overflow-hidden">
               <table className="premium-table w-full text-left">
                  <thead className="bg-slate-50/50">
                     <tr className="text-[10px] text-slate-400 font-bold uppercase tracking-widest border-b border-slate-100">
                        <th className="pl-6 py-4">High-Value Asset</th>
                        <th>Identity</th>
                        <th>Ownership Tenure</th>
                        <th>Automation Loop</th>
                        <th className="pr-6 text-right">Action</th>
                     </tr>
                  </thead>
                  <tbody>
                     {anniversaries.map((app, i) => {
                        const years = app.tenure_years || (Math.floor(Math.random() * 5) + 2); // Use actual tenure if available, else simulate
                        return (
                           <tr key={i} className="hover:bg-slate-50/50 transition border-b border-slate-50 last:border-none group">
                              <td className="pl-6 py-5">
                                 <p className="font-semibold text-slate-800 text-[13px]">{app.address}</p>
                                 <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tight">EST. VALUE: $1.2M - $1.4M</p>
                              </td>
                              <td className="text-sm font-medium text-slate-600">{app.full_name}</td>
                              <td>
                                 <div className="flex items-center gap-2">
                                    <span className="text-xl font-bold text-indigo-600 tracking-tighter">{years}Y</span>
                                    <span className="text-[10px] font-bold text-slate-300 uppercase leading-none">Tenure</span>
                                 </div>
                              </td>
                              <td>
                                 <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                    <span className="text-[10px] font-bold text-indigo-500 py-1 px-2 bg-indigo-50 rounded uppercase tracking-tighter">PHASE: APPR TRIGGER</span>
                                 </div>
                              </td>
                              <td className="pr-6 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                 <div className="flex items-center gap-2 justify-end">
                                    <button
                                       onClick={() => setActiveModal('APPRAISAL_CALCULATOR')}
                                       className="px-4 py-2 bg-white border border-slate-100 text-indigo-600 text-[9px] font-bold uppercase tracking-widest rounded-lg hover:border-indigo-100 flex items-center gap-2">
                                       <Calculator size={12} /> Appraisal Calc
                                    </button>
                                    <button
                                       onClick={() => setActiveModal('ANNIVERSARY_LETTER')}
                                       className="px-4 py-2 bg-slate-50 border border-slate-100 text-slate-800 text-[9px] font-bold uppercase tracking-widest rounded-lg hover:border-indigo-100 flex items-center gap-2">
                                       <FileText size={12} /> Generate Letter
                                    </button>
                                 </div>
                              </td>
                           </tr>
                        );
                     })}
                  </tbody>
               </table>
            </div>
         </div>
      );
   };

   const renderAppraisals = () => (
      <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300 pb-12">
         <div className="flex items-center justify-between px-2">
            <div>
               <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Appraisal Management</h2>
               <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Conversion Hub: AI Lead ➔ Physical Booking</p>
            </div>
            <button
               onClick={() => setActiveModal('BOOK_APPRAISAL')}
               className="btn-premium px-8">
               <Plus size={14} /> Book New Appraisal
            </button>
         </div>

         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="premium-card p-6 border-l-4 border-l-indigo-500">
               <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest">Awaiting Sync</span>
                  <Clock size={16} className="text-slate-300" />
               </div>
               <h3 className="text-2xl font-bold text-slate-800 leading-none mb-1">14</h3>
               <p className="text-xs text-slate-400 font-medium">Leads interested in appraisal via AI call</p>
            </div>
            <div className="premium-card p-6 border-l-4 border-l-emerald-500">
               <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Active Bookings</span>
                  <Calendar size={16} className="text-slate-300" />
               </div>
               <h3 className="text-2xl font-bold text-slate-800 leading-none mb-1">08</h3>
               <p className="text-xs text-slate-400 font-medium">Physical meetings scheduled this week</p>
            </div>
            <div className="premium-card p-6 border-l-4 border-l-rose-500">
               <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-bold text-rose-600 uppercase tracking-widest">Cycle Triggers</span>
                  <Zap size={16} className="text-slate-300" />
               </div>
               <h3 className="text-2xl font-bold text-slate-800 leading-none mb-1">04</h3>
               <p className="text-xs text-slate-400 font-medium">Automatic appraisal loops detected</p>
            </div>
         </div>

         <div className="premium-card overflow-hidden">
            <table className="premium-table w-full text-left">
               <thead className="bg-slate-50/50"><tr className="text-[10px] text-slate-400 font-bold uppercase tracking-widest border-b border-slate-100"><th className="pl-8 py-4">Target Address</th><th>Property Owner</th><th>AI Qualification Status</th><th className="pr-8 text-right">Action</th></tr></thead>
               <tbody className="divide-y divide-slate-50">
                  {anniversaries.length > 0 ? anniversaries.map((app, i) => (
                     <tr key={i} className="hover:bg-slate-50/50 transition">
                        <td className="pl-8 py-5 font-bold text-slate-800 text-sm whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">{app.address}</td>
                        <td className="text-sm font-semibold text-slate-600">{app.full_name}</td>
                        <td><span className="px-2 py-1 bg-emerald-50 text-emerald-600 text-[10px] font-bold rounded flex items-center gap-2 w-max shadow-sm"><CheckCircle2 size={12} /> AI QUALIFIED</span></td>
                        <td className="pr-8 text-right">
                           <button
                              onClick={() => setActiveModal('BOOK_APPRAISAL')}
                              className="px-4 py-2 bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-widest rounded-lg shadow-lg shadow-indigo-100 flex items-center gap-2 ml-auto">
                              Book Meeting <ArrowRight size={12} />
                           </button>
                        </td>
                     </tr>
                  )) : (
                     <tr><td colSpan={4} className="py-20 text-center text-slate-300 font-bold uppercase tracking-widest">No active appraisal triggers found</td></tr>
                  )}
               </tbody>
            </table>
         </div>
      </div>
   );

   const renderCampaigns = () => (
      <div className="max-w-4xl mx-auto space-y-12 animate-in fade-in duration-500 pb-32 pt-8">
         <div className="flex flex-col md:flex-row items-center justify-between px-4 gap-6">
            <div className="text-center md:text-left">
               <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Personalized Sequence Master</h2>
               <p className="text-[10px] text-indigo-500 font-bold uppercase tracking-[0.2em] mt-1 flex items-center justify-center md:justify-start gap-2">
                  <Zap size={12} className="fill-indigo-500" /> Professional Blueprint Node: Active
               </p>
            </div>
            <div className="flex items-center gap-4">
               <div className="px-4 py-2 bg-slate-50 border border-slate-100 rounded-xl">
                  <p className="text-[9px] font-bold text-slate-400 uppercase mb-1">Available Tags</p>
                  <p className="text-[10px] font-mono font-bold text-indigo-600">[Name] [Address] [Date]</p>
               </div>
               <button onClick={() => setActiveModal('LAUNCH_CAMPAIGN')} className="btn-premium px-10 py-3.5 shadow-2xl shadow-indigo-100">Global Launch</button>
            </div>
         </div>

         <div className="relative flex flex-col items-center gap-12">
            {/* Visual Vertical Connection Line */}
            <div className="absolute top-0 left-1/2 w-[2px] h-full bg-indigo-50 -translate-x-1/2 z-0"></div>

            {/* Stage 1: Segment Isolation */}
            <div className="w-full relative z-10 group">
               <div className="premium-card p-6 border-indigo-200 bg-white hover:shadow-2xl hover:shadow-indigo-100/50 transition-all">
                  <div className="flex items-start gap-6">
                     <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-indigo-200"><Users size={28} /></div>
                     <div className="flex-1">
                        <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mb-1">Trigger Cluster: 01</p>
                        <h4 className="text-lg font-bold text-slate-900">Year 2 Matrix Cluster</h4>
                        <p className="text-xs text-slate-400 font-medium">Auto-filtering owners for the Silverdale/Rodney expansion zone.</p>
                     </div>
                  </div>
               </div>
            </div>

            {/* Stage 2: Email Loop */}
            <div className="w-full relative z-10 group">
               <div className="absolute -left-4 top-1/2 -translate-y-1/2 w-8 h-8 bg-indigo-600 rounded-full border-4 border-white flex items-center justify-center text-white text-[10px] font-bold shadow-lg">2</div>
               <div className="premium-card p-8 border-slate-100 hover:border-indigo-100 bg-white transition-all">
                  <div className="flex flex-col md:flex-row gap-8">
                     <div className="w-full md:w-1/3 space-y-4">
                        <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-indigo-600 border border-slate-100"><Mail size={22} /></div>
                        <h4 className="text-sm font-bold text-slate-900">Email Ghostwriter</h4>
                        <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                           <p className="text-[9px] font-bold text-indigo-600 uppercase mb-1">Automation Setting</p>
                           <div className="flex items-center justify-between text-[10px] font-bold text-slate-600 border-none outline-none">
                              <span>Wait time</span>
                              <input type="text" defaultValue="15m" className="w-12 text-right bg-transparent border-none outline-none text-indigo-600 font-black cursor-text" />
                           </div>
                        </div>
                     </div>
                     <div className="w-full md:w-2/3 space-y-4">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Personalized Template (Editable)</label>
                        <textarea 
                           className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-[11px] font-medium leading-relaxed text-slate-700 h-32 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                           placeholder="Write your email here..."
                           value={emailTemplate}
                           onChange={(e) => setEmailTemplate(e.target.value)}
                        />
                        <div className="flex gap-2">
                           <button onClick={() => handleRewrite('email')} className="flex-1 py-2.5 bg-slate-900 text-white text-[9px] font-bold uppercase tracking-widest rounded-xl hover:bg-slate-800 transition-all">Regenerate with AI</button>
                           <button onClick={() => handleLaunchCampaign('email')} className="flex-1 py-2.5 bg-indigo-600 text-white text-[9px] font-bold uppercase tracking-widest rounded-xl hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100">Execute Email Pulse</button>
                           <button onClick={() => setEmailTemplate("Hi [Name],\n\nKarin was just reviewing your 2-year settlement anniversary at [Address]. Rodney market data shows a strong upward drift since [Date].\n\nWould you be open to seeing the fresh valuation report my AI engine just drafted for you?")} className="px-4 py-2.5 bg-white border border-slate-100 text-slate-400 text-[9px] font-bold uppercase tracking-widest rounded-xl hover:text-indigo-600 hover:border-indigo-100 transition-all">Reset</button>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* Stage 3: SMS Pulse */}
            <div className="w-full relative z-10 group">
               <div className="absolute -left-4 top-1/2 -translate-y-1/2 w-8 h-8 bg-emerald-500 rounded-full border-4 border-white flex items-center justify-center text-white text-[10px] font-bold shadow-lg">3</div>
               <div className="premium-card p-8 border-slate-100 hover:border-emerald-100 bg-white transition-all">
                  <div className="flex flex-col md:flex-row gap-8">
                     <div className="w-full md:w-1/3 space-y-4">
                        <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 border border-emerald-100"><Smartphone size={22} /></div>
                        <h4 className="text-sm font-bold text-slate-900">SMS Confirmation Pulse</h4>
                        <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-100">
                           <p className="text-[9px] font-bold text-emerald-600 uppercase mb-1">Automation Setting</p>
                           <div className="flex items-center justify-between text-[10px] font-bold text-slate-600">
                              <span>Send after email</span>
                              <input type="text" defaultValue="2h" className="w-12 text-right bg-transparent border-none outline-none text-emerald-600 font-black" />
                           </div>
                        </div>
                     </div>
                     <div className="w-full md:w-2/3 space-y-4">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">SMS Template (Editable)</label>
                        <textarea 
                           className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-[11px] font-medium leading-relaxed text-slate-700 h-24 focus:ring-2 focus:ring-emerald-100 outline-none transition-all"
                           value={smsTemplate}
                           onChange={(e) => setSmsTemplate(e.target.value)}
                        />
                        <div className="flex gap-2">
                           <button onClick={() => handleRewrite('sms')} className="flex-1 py-2.5 bg-emerald-600 text-white text-[9px] font-bold uppercase tracking-widest rounded-xl hover:bg-slate-900 transition-all">Refine Tone with AI</button>
                           <button onClick={() => handleLaunchCampaign('sms')} className="flex-1 py-2.5 bg-slate-900 text-white text-[9px] font-bold uppercase tracking-widest rounded-xl hover:bg-black transition-all shadow-lg shadow-slate-200">Execute SMS Pulse</button>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* Stage 4: Voice Vapi Wave */}
            <div className="w-full relative z-10 group">
               <div className="absolute -left-4 top-1/2 -translate-y-1/2 w-8 h-8 bg-slate-900 rounded-full border-4 border-white flex items-center justify-center text-white text-[10px] font-bold shadow-lg">4</div>
               <div className="premium-card p-8 border-slate-900 bg-slate-900 text-white shadow-2xl shadow-indigo-200">
                  <div className="flex flex-col md:flex-row gap-8 items-center">
                     <div className="w-full md:w-1/3 space-y-4">
                        <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-indigo-600/30"><PhoneCall size={22} /></div>
                        <h4 className="text-sm font-bold">VAPI Voice Engine</h4>
                        <div className="flex items-center gap-2 text-[8px] font-bold text-indigo-400 uppercase bg-white/5 p-2 rounded-lg border border-white/10 w-fit">
                           <ShieldCheck size={12} /> SECURE TRIGGER ACTIVE
                        </div>
                     </div>
                     <div className="w-full md:w-2/3 flex flex-col items-center md:items-start text-center md:text-left gap-2">
                        <h4 className="text-lg font-bold italic tracking-tight text-indigo-400">Final Qualification Protocol</h4>
                        <p className="text-xs text-slate-400 font-medium leading-relaxed max-w-[400px]">The system will automatically trigger your **Vapi Outbound Agent** on day 2 to conduct the 3-minute listing discovery call with [Name].</p>
                        <div className="mt-4 px-4 py-2 bg-white/5 rounded-xl border border-white/10 text-[9px] font-bold text-indigo-300 uppercase tracking-widest">Target Delay: 24h from entry</div>
                     </div>
                  </div>
               </div>
         </div>
      </div>

      <div className="premium-card p-0 bg-white border border-slate-100 overflow-hidden mt-12">
         <div className="p-6 border-b border-slate-50 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest">Historical Wave Analytics</h3>
            <button className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest hover:underline">Download Master Report</button>
         </div>
         <table className="w-full text-left">
            <thead className="bg-slate-50/50">
               <tr className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em] border-b border-slate-100">
                  <th className="pl-6 py-4">Campaign Cluster</th>
                  <th>Protocol Flow</th>
                  <th>Engagement</th>
                  <th className="pr-6 text-right">Status</th>
               </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
               {[
                  { name: 'Cold Lead Re-engagement', flow: 'E -> S', conversion: '12%', status: 'Completed' },
                  { name: 'Silverdale Anniversary Wave', flow: 'E -> S -> V', conversion: '28%', status: 'Active' },
               ].map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50/30 transition group">
                     <td className="pl-6 py-5 font-bold text-slate-800 text-xs">{row.name}</td>
                     <td className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest">{row.flow}</td>
                     <td className="text-[10px] font-bold text-slate-500 uppercase">{row.conversion}</td>
                     <td className="pr-6 text-right"><span className={`px-2 py-1 rounded text-[9px] font-bold uppercase tracking-tighter ${row.status === 'Active' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-300'}`}>{row.status}</span></td>
                  </tr>
               ))}
            </tbody>
         </table>
      </div>
   </div>
);

   const renderSettings = () => (
      <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300 pb-12">
         <div className="px-2">
            <h2 className="text-lg font-semibold text-slate-800 tracking-tight">System Configuration</h2>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Global Protocol & Communication Keys</p>
         </div>

         <div className="space-y-4">
            <div className="premium-card p-8 space-y-6">
                <div className="flex items-start justify-between">
                   <div className="space-y-1">
                      <h4 className="text-sm font-bold text-slate-800">Google Ecosystem Sync</h4>
                      <p className="text-xs text-slate-400">Sync with Gmail and Google Calendar for automated communications.</p>
                   </div>
                   <button 
                      onClick={handleConnectGoogle}
                      className={`px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all ${googleConnected ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-indigo-600 text-white shadow-lg shadow-indigo-100 active:scale-95'}`}>
                      {googleConnected ? '✓ GOOGLE CONNECTED' : 'CONNECT GOOGLE ACCOUNT'}
                   </button>
                </div>
            </div>

            <div className="premium-card p-8 space-y-8">
               <div className="flex items-start justify-between">
                  <div className="space-y-1">
                     <h4 className="text-sm font-bold text-slate-800">Vapi.ai Voice Handshake</h4>
                     <p className="text-xs text-slate-400">Configure your ultra-low latency API keys for AI Phone Calls.</p>
                  </div>
                  <div className="px-3 py-1 bg-emerald-50 text-emerald-600 text-[10px] font-bold rounded border border-emerald-100 flex items-center gap-2 tracking-widest">CONNECTED</div>
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Vapi Public Key</label>
                     <input type="password" value="************************" readOnly className="w-full bg-slate-50 border border-slate-100 rounded-xl py-3 px-4 text-xs font-bold text-slate-400 outline-none" />
                  </div>
                  <div className="space-y-2">
                     <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">WhatsApp Token</label>
                     <input type="password" value="************************" readOnly className="w-full bg-slate-50 border border-slate-100 rounded-xl py-3 px-4 text-xs font-bold text-slate-400 outline-none" />
                  </div>
               </div>
            </div>

            <div className="premium-card p-8 space-y-6">
               <div className="space-y-1">
                  <h4 className="text-sm font-bold text-slate-800">Communication Timeline Protocol</h4>
                  <p className="text-xs text-slate-400">Define the delays between Email, SMS, and AI Voice sequences.</p>
               </div>
               <div className="space-y-6">
                  {[
                     { label: 'Phase 1 Delay (Email ➔ SMS)', val: '15 Minutes' },
                     { label: 'Phase 2 Delay (SMS ➔ AI Call)', val: '2 Hours' },
                     { label: 'Outbound Campaign Delay', val: '24 Hours' },
                  ].map((item, i) => (
                     <div key={i} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100/50">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">{item.label}</span>
                        <div className="flex items-center gap-4 text-sm font-bold text-indigo-600">
                           {item.val}
                           <button className="p-1 rounded bg-white border border-slate-100 text-slate-300 hover:text-indigo-600 transition"><Sliders size={14} /></button>
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         </div>

         <div className="flex justify-end gap-3 pr-2">
            <button className="px-8 py-3 bg-slate-100 text-slate-400 font-bold text-xs rounded-xl hover:bg-slate-200 transition">Factory Reset</button>
            <button className="px-10 py-3 bg-indigo-600 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-100 hover:bg-slate-900 transition flex items-center gap-2"><Send size={14} /> Save Global Sync</button>
         </div>
      </div>
   );

   const renderInteractions = () => (
      <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300 pb-12">
         <div className="flex items-center justify-between px-2">
            <div>
               <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Interaction Records</h2>
               <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">High-Fidelity Audit Trail of Agent Actions</p>
            </div>
            <ShieldCheck size={20} className="text-emerald-500" />
         </div>
         <div className="premium-card overflow-hidden">
            <table className="premium-table w-full text-left bg-white">
               <thead className="bg-slate-50/50">
                  <tr className="text-[10px] text-slate-400 font-bold uppercase tracking-widest border-b border-slate-100">
                     <th className="pl-8 py-4">Participant</th>
                     <th>Interaction Content</th>
                     <th>Channel/Type</th>
                     <th className="pr-8 text-right">Timestamp</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-slate-50">
                  {interactions.map((log, i) => (
                     <tr key={i} className="hover:bg-slate-50/30 transition group">
                        <td className="pl-8 py-5">
                           <div className="flex items-center gap-3">
                              <div className={`w-2 h-2 rounded-full ${log.direction === 'inbound' ? 'bg-indigo-600' : 'bg-emerald-500'}`}></div>
                              <span className="text-xs font-bold text-slate-800 uppercase tracking-tighter">AGENT NODE #{log.id}</span>
                           </div>
                        </td>
                        <td className="text-[13px] font-medium text-slate-600 max-w-md truncate pr-10">{log.content}</td>
                        <td><div className="flex items-center gap-2"><span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-[9px] font-bold rounded uppercase">{log.channel}</span><span className={`text-[9px] font-bold uppercase ${log.direction === 'inbound' ? 'text-indigo-600' : 'text-emerald-600'}`}>{log.direction}</span></div></td>
                        <td className="pr-8 text-right text-[10px] font-bold text-slate-300 uppercase">{new Date(log.created_at).toLocaleString()}</td>
                     </tr>
                  ))}
               </tbody>
            </table>
         </div>
      </div>
   );

   return (
      <div className="flex h-screen bg-[#FBFBFE]">
         {/* Absolute Header Gradient Glow */}
         <div className="fixed top-0 left-0 w-full h-[300px] bg-gradient-to-b from-indigo-500/5 to-transparent pointer-events-none z-0"></div>

         {/* Minimalism Control Sidebar */}
         <aside className="w-20 lg:w-52 premium-sidebar pt-6 shadow-[1px_0_20px_rgba(0,0,0,0.01)] relative z-20">
            <div className="flex items-center gap-3 px-6 mb-8 group cursor-pointer transition-all">
               <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-xl shadow-indigo-100 active:scale-95 transition-transform"><Activity size={16} strokeWidth={3} /></div>
               <p className="hidden lg:block font-bold text-sm tracking-tight text-slate-800 uppercase leading-none select-none">Karin AI</p>
            </div>

            <nav className="flex-1 px-3 space-y-0.5 custom-scrollbar overflow-y-auto relative z-10">
               {[
                  { id: 'dashboard', icon: Home, label: 'Dashboard', path: '/' },
                  { id: 'leads', icon: TrendingUp, label: 'Pipeline', path: '/leads' },
                  { id: 'anniversaries', icon: Building, label: 'Anniversaries', path: '/anniversaries' },
                  { id: 'clients', icon: Users, label: 'Clients', path: '/clients' },
                  { id: 'appraisals', icon: ClipboardList, label: 'Appraisals', path: '/appraisals' },
                  { id: 'campaigns', icon: PhoneCall, label: 'Campaigns', path: '/campaigns' },
                  { id: 'interactions', icon: History, label: 'Logs', path: '/interactions' },
               ].map((item) => (
                  <button key={item.id} onClick={() => navigate(item.path)} className={`nav-item w-full ${activeTab === item.id ? 'nav-item-active' : 'nav-item-inactive'}`}>
                     <item.icon size={16} strokeWidth={2.5} />
                     <span className="hidden lg:block font-semibold text-[10px] uppercase tracking-wider">{item.label}</span>
                  </button>
               ))}
            </nav>

            <div className="p-4 mt-auto">
               <button onClick={() => navigate('/settings')} className={`nav-item w-full ${activeTab === 'settings' ? 'nav-item-active' : 'nav-item-inactive'}`}>
                  <Settings size={16} strokeWidth={2.5} />
                  <span className="hidden lg:block font-semibold text-[10px] uppercase tracking-wider">Settings</span>
               </button>
            </div>
         </aside>

         <main className="flex-1 flex flex-col overflow-hidden relative z-10">
            <header className="h-14 glass-header flex items-center justify-between px-8 shrink-0 z-10">
               <div className="flex flex-col">
                  <h1 className="text-sm font-semibold text-slate-900 tracking-tight leading-none capitalize select-none">{activeTab.replace('_', ' ')} Hub</h1>
               </div>

               <div className="flex items-center gap-6">
                  <button
                     onClick={() => showToast(googleConnected ? 'Google Calendar Sync Active [Karin@cooperandco.co.nz]' : 'Please link your Google account in Settings.', 'info')}
                     className={`hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-widest transition-all ${googleConnected ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-indigo-50 text-indigo-600 border-indigo-100'}`}>
                     {googleConnected ? <CheckCircle2 size={12} /> : <Link size={12} />} 
                     {googleConnected ? 'Calendar Active' : 'Link Calendar'}
                  </button>
                  <div className="relative hidden md:block group">
                     <input type="text" placeholder="Omni searching..." className="bg-slate-50 border-none rounded-lg py-1.5 pl-10 pr-4 w-40 text-[10px] font-semibold tracking-tight focus:w-80 transition-all outline-none" />
                     <Search className="absolute left-4 top-2 text-slate-300" size={14} />
                  </div>

                  <div className="flex items-center gap-4">
                     <Bell size={18} className="text-slate-400 group cursor-pointer hover:text-indigo-600 transition-colors" />
                     <div className="h-6 w-[1px] bg-slate-100"></div>
                     <div className="flex items-center gap-3 cursor-pointer group">
                        <div className="text-right leading-none hidden sm:block">
                           <p className="font-bold text-xs text-[#0F172A] tracking-tighter mb-0.5 select-none">Karin Blaauw</p>
                           <p className="text-[9px] text-indigo-600 font-bold uppercase tracking-widest select-none">Executive Agent</p>
                        </div>
                        <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=64&h=64" className="w-9 h-9 rounded-lg border border-slate-100 shadow-sm object-cover ring-1 ring-slate-50" alt="Profile" />
                     </div>
                  </div>
               </div>
            </header>

            <div className="flex-1 p-8 overflow-y-auto custom-scrollbar bg-[#FAFBFF]">
               {loading ? (
                  <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4 opacity-30">
                     <div className="w-8 h-8 border-2 border-slate-100 border-t-indigo-600 rounded-full animate-spin"></div>
                     <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Syncing Intelligence Node...</p>
                  </div>
               ) : (
                  <div className="animate-in fade-in duration-700 ease-out">
                     <Routes>
                        <Route path="/" element={renderDashboard()} />
                        <Route path="/dashboard" element={renderDashboard()} />
                        <Route path="/leads" element={renderLeads()} />
                        <Route path="/clients" element={renderClients()} />
                        <Route path="/anniversaries" element={renderAnniversaries()} />
                        <Route path="/appraisals" element={renderAppraisals()} />
                        <Route path="/campaigns" element={renderCampaigns()} />
                        <Route path="/interactions" element={renderInteractions()} />
                        <Route path="/settings" element={renderSettings()} />
                     </Routes>
                  </div>
               )}
            </div>
         </main>

         {/* Premium System Modal Overlay */}
         {activeModal && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-[#0F172A]/40 backdrop-blur-sm animate-in fade-in duration-300">
               <div className="bg-white w-full max-w-xl rounded-3xl shadow-2xl border border-slate-100 overflow-hidden animate-in zoom-in-95 duration-200">
                  <div className="p-8 pb-4 flex items-center justify-between">
                     <div>
                        <h3 className="text-xl font-bold text-slate-900 tracking-tight capitalize leading-none mb-2">{activeModal?.replace('_', ' ')}</h3>
                        <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Karin AI Internal System Hub</p>
                     </div>
                     <button onClick={closeModals} className="p-3 bg-slate-50 text-slate-300 rounded-xl hover:text-slate-900 transition"><X size={18} /></button>
                  </div>

                  {activeModal === 'RECORD_LEAD' && (
                     <div className="px-8 flex gap-8 border-b border-slate-50">
                        <button onClick={() => setModalTab('MANUAL')} className={`pb-3 text-[10px] font-bold uppercase tracking-widest transition-all ${modalTab === 'MANUAL' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-300'}`}>Manual Entry</button>
                        <button onClick={() => setModalTab('IMPORT')} className={`pb-3 text-[10px] font-bold uppercase tracking-widest transition-all ${modalTab === 'IMPORT' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-300'}`}>Database Handshake</button>
                     </div>
                  )}

                  <div className="p-8 pt-6 space-y-6">
                     {activeModal === 'RECORD_LEAD' && modalTab === 'MANUAL' && (
                        <div className="space-y-6">
                           <div className="p-4 bg-indigo-50/30 border border-indigo-100/50 rounded-2xl flex items-center gap-4">
                              <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white"><Users size={20} /></div>
                              <div><p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest">Lead Instruction</p><p className="text-[11px] text-slate-500 font-medium">Entering this record will trigger the 3-step AI follow-up (Email ➔ SMS ➔ Call).</p></div>
                           </div>
                           <div className="grid grid-cols-2 gap-6">
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Client Full Name</label><input type="text" placeholder="e.g. John Doe" value={formData.name || ''} onChange={(e) => setFormData({...formData, name: e.target.value})} className="input-premium" /></div>
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Mobile Stream (NZ +64)</label><input type="text" placeholder="+64 21 000 000" value={formData.phone || ''} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="input-premium" /></div>
                           </div>
                           <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Property Hub Address</label><input type="text" placeholder="123 Silverdale Road, Rodney..." value={formData.address || ''} onChange={(e) => setFormData({...formData, address: e.target.value})} className="input-premium" /></div>
                           <div className="grid grid-cols-2 gap-6">
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Purchase Date</label><input type="date" value={formData.purchase_date || ''} onChange={(e) => setFormData({...formData, purchase_date: e.target.value})} className="input-premium" /></div>
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Client Email</label><input type="email" placeholder="client@example.com" value={formData.email || ''} onChange={(e) => setFormData({...formData, email: e.target.value})} className="input-premium" /></div>
                           </div>
                        </div>
                     )}

                     {activeModal === 'RECORD_LEAD' && modalTab === 'IMPORT' && (
                        <div className="space-y-6">
                           <label className="p-8 border-2 border-dashed border-indigo-100 bg-slate-50/50 rounded-2xl flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-100/50 transition-all group overflow-hidden">
                              <input type="file" className="hidden" onChange={handleImport} />
                              <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-indigo-600 mb-4 border border-slate-50 group-hover:scale-110 transition-transform"><Upload size={18} /></div>
                              <div className="space-y-1">
                                 <h4 className="text-[11px] font-bold text-slate-900 uppercase tracking-widest">Automatic Portfolio Sync</h4>
                                 <p className="text-[10px] text-slate-400 font-medium max-w-[220px] leading-relaxed">Drag your database file here or <span className="text-indigo-600 font-bold">click to browse</span></p>
                              </div>
                           </label>
                        </div>
                     )}

                     {activeModal === 'BOOK_APPRAISAL' && (
                        <div className="space-y-6 text-sm">
                           <div className="p-4 bg-emerald-50/30 border border-emerald-100/50 rounded-2xl flex items-center gap-4">
                              <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-white"><CheckCircle2 size={20} /></div>
                              <div><p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Qualified Status Found</p><p className="text-[11px] text-slate-500 font-medium leading-tight">AI Voice conversation confirmed interest for a physical appraisal booking.</p></div>
                           </div>
                           <div className="grid grid-cols-2 gap-6">
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Meeting Date</label><input type="date" value={formData.date || ''} onChange={(e) => setFormData({...formData, date: e.target.value})} className="input-premium" /></div>
                              <div className="space-y-2"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Time Window</label><select className="input-premium" value={formData.time || ''} onChange={(e) => setFormData({...formData, time: e.target.value})}><option>Morning: 9am - 12pm</option><option>Afternoon: 1pm - 5pm</option></select></div>
                           </div>
                        </div>
                     )}

                   {activeModal === 'LAUNCH_CAMPAIGN' && (
                      <div className="space-y-6">
                         <div className="space-y-3">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Live Segment: Year 2 Owners ({anniversaries.length})</label>
                            <div className="max-h-40 overflow-y-auto custom-scrollbar border border-slate-50 rounded-2xl bg-slate-50/30 p-4 space-y-2">
                               {anniversaries.length > 0 ? anniversaries.map((client, idx) => (
                                  <div key={idx} className="flex items-center justify-between py-2 border-b border-white/50 last:border-none">
                                     <div className="flex items-center gap-3">
                                        <div className="w-7 h-7 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center text-[10px] font-black">{client.name[0]}</div>
                                        <div>
                                           <p className="text-[11px] font-bold text-slate-700 leading-none mb-1">{client.name}</p>
                                           <p className="text-[9px] text-slate-400 font-medium">{client.property_address}</p>
                                        </div>
                                     </div>
                                     <div className="flex items-center gap-2">
                                        <div className="px-2 py-0.5 bg-emerald-100 text-emerald-600 text-[8px] font-black rounded uppercase">Ready</div>
                                     </div>
                                  </div>
                               )) : (
                                  <p className="text-[10px] text-slate-400 font-medium text-center py-4">No owners identified for this segment yet.</p>
                               )}
                            </div>
                         </div>
                         <div className="space-y-4">
                            <div className="p-4 bg-indigo-900 rounded-2xl text-white flex items-center justify-between shadow-xl shadow-indigo-100">
                               <div className="space-y-1">
                                  <p className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest">Protocol Strategy</p>
                                  <h4 className="text-xs font-bold">ANNIVERSARY_WAVE_V1</h4>
                               </div>
                               <div className="flex flex-col items-end">
                                  <p className="text-[9px] font-bold text-indigo-400 uppercase">Estimated Reach</p>
                                  <h4 className="text-xs font-black">{anniversaries.length} Owners</h4>
                               </div>
                            </div>
                            <button 
                               onClick={() => {
                                  showToast('Dispatching Automated Wave... Grok is syncing drafts.', 'success');
                                  closeModals();
                               }}
                               disabled={anniversaries.length === 0}
                               className="w-full py-4 bg-indigo-600 text-white font-black text-[11px] uppercase tracking-[0.2em] rounded-2xl shadow-2xl shadow-indigo-200 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:grayscale">
                               START DISPATCH WAVE
                            </button>
                         </div>
                      </div>
                   )}

                     {activeModal === 'ANNIVERSARY_LETTER' && (
                        <div className="space-y-4">
                           <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl">
                              <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mb-3">AI PROTOTYPE: ANNIVERSARY_LETTER.PDF</p>
                              <div className="space-y-3 font-serif text-[11px] leading-relaxed text-slate-600">
                                 <p>Dear Valued Client,</p>
                                 <p>It has been exactly 2 years since you settled into your property at <strong>Silverdale Road</strong>. I wanted to reach out with a personal gift: my latest update on the market value of your home.</p>
                                 <p>Since your purchase, the Rodney market has evolved significantly. I've drafted a fresh appraisal for your review...</p>
                              </div>
                           </div>
                           <div className="space-y-2">
                              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Distribution Method</label>
                              <div className="flex gap-2">
                                 <button className="flex-1 py-1.5 bg-indigo-50 text-indigo-600 text-[10px] font-bold rounded-lg border border-indigo-100">EMAIL PDF</button>
                                 <button className="flex-1 py-1.5 bg-white text-slate-300 text-[10px] font-bold rounded-lg border border-slate-100 uppercase">PHYSICAL MAIL</button>
                              </div>
                           </div>
                        </div>
                     )}

                     {activeModal === 'APPRAISAL_CALCULATOR' && (
                        <div className="space-y-4">
                           <div className="grid grid-cols-2 gap-4">
                              <div className="space-y-2">
                                 <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Original Purchase Price</label>
                                 <div className="relative"><DollarSign className="absolute left-3 top-3.5 text-slate-300" size={14} /><input type="text" defaultValue="1,200,000" className="input-premium pl-8" /></div>
                              </div>
                              <div className="space-y-2">
                                 <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Rodney Market Index (+/-% )</label>
                                 <div className="relative"><TrendingUp className="absolute left-3 top-3.5 text-slate-300" size={14} /><input type="text" defaultValue="8.4" className="input-premium pl-8" /></div>
                              </div>
                           </div>
                           <div className="p-5 bg-indigo-900 rounded-3xl text-white space-y-4 shadow-xl shadow-indigo-100">
                              <div className="flex items-center justify-between">
                                 <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400">Calculated Market Drift</span>
                                 <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-500 rounded-full text-white">UPWARD TREND</span>
                              </div>
                              <div className="flex flex-col gap-1">
                                 <h4 className="text-3xl font-bold tracking-tighter leading-none">$1,300,800 - $1,425,000</h4>
                                 <p className="text-[11px] font-medium text-indigo-300 italic opacity-80">Based on property anniversary cycle (Year 2)</p>
                              </div>
                              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
                                 <div><p className="text-[9px] font-bold text-indigo-400 uppercase mb-1">Total Appreciation</p><p className="text-lg font-bold">+$100,800</p></div>
                                 <div><p className="text-lg font-bold">8.4% YoY</p></div>
                              </div>
                           </div>
                           <button
                              onClick={() => { setActiveModal('ANNIVERSARY_LETTER'); showToast('Valuation logic injected into draft.', 'success'); }}
                              className="w-full py-3 bg-white border border-indigo-100 text-indigo-600 font-bold text-[10px] uppercase tracking-widest rounded-xl hover:bg-slate-50 transition-all">
                              Inject Into Anniversary Letter Flow
                           </button>
                        </div>
                     )}

                     <div className="pt-4 flex items-center gap-3">
                        <button onClick={closeModals} className="flex-1 py-3.5 bg-slate-50 text-slate-400 font-bold text-[11px] uppercase tracking-widest rounded-xl hover:bg-slate-100 transition active:scale-95">Cancel</button>
                        <button
                           onClick={handleExecuteProtocol}
                           className="flex-[2] py-3.5 bg-indigo-600 text-white font-bold text-[11px] uppercase tracking-widest rounded-xl shadow-xl shadow-indigo-100 hover:bg-slate-900 transition active:scale-95 flex items-center justify-center gap-2">
                           <Send size={14} /> Execute Protocol
                        </button>
                     </div>
                  </div>
               </div>
            </div>
         )}

         {/* Global Success Feedback Notification */}
         {toast && (
            <div className="fixed bottom-8 right-8 z-[100] animate-in slide-in-from-right-10 duration-500">
               <div className={`p-4 rounded-2xl shadow-2xl border flex items-center gap-4 ${toast.type === 'success' ? 'bg-white border-emerald-100' : 'bg-slate-900 border-indigo-500'} min-w-[320px]`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${toast.type === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-indigo-600 text-white'}`}>
                     {toast.type === 'success' ? <CheckCircle2 size={20} /> : <Activity size={20} />}
                  </div>
                  <div>
                     <p className={`text-[10px] font-bold uppercase tracking-[0.2em] mb-0.5 ${toast.type === 'success' ? 'text-emerald-400' : 'text-indigo-400'}`}>System Protocol</p>
                     <p className={`text-xs font-semibold ${toast.type === 'success' ? 'text-slate-800' : 'text-white'}`}>{toast.message}</p>
                  </div>
               </div>
            </div>
         )}
      </div>
   );
};

export default App;
