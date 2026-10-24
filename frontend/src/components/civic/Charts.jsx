import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Empty } from "@/components/civic/ui";

const tick = { fontSize: 10, fill: "#64748b", fontFamily: "DM Mono" };
const tip = { contentStyle: { border: "1px solid #e2e8f0", borderRadius: 0, fontSize: 12 } };

export function ProgressChart({ projects }) {
  if (!projects.length) return <Empty>No projects yet.</Empty>;
  const data = projects.map(p => ({ name: p.code, progress: p.progress, project: p.name }));
  return <div className="chart-box" data-testid="progress-chart"><ResponsiveContainer width="100%" height={220}>
    <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16 }}><CartesianGrid horizontal={false} stroke="#eef2f7" />
      <XAxis type="number" domain={[0, 100]} tick={tick} unit="%" /><YAxis type="category" dataKey="name" tick={tick} width={56} />
      <Tooltip {...tip} formatter={v => [`${v}%`, "Progress"]} labelFormatter={(l, p) => p?.[0]?.payload.project || l} />
      <Bar dataKey="progress" fill="#d97706" barSize={14} /></BarChart></ResponsiveContainer></div>;
}

const SEV = { High: "#dc2626", Medium: "#d97706", Low: "#2563eb" };
export function SeverityChart({ data }) {
  const total = data.reduce((a, d) => a + d.value, 0);
  if (!total) return <Empty testid="severity-empty">No open issues. Nice work.</Empty>;
  return <div className="chart-box" data-testid="severity-chart"><ResponsiveContainer width="100%" height={220}>
    <PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} stroke="none">{data.map(d => <Cell key={d.name} fill={SEV[d.name]} />)}</Pie>
      <Tooltip {...tip} /><Legend iconType="square" wrapperStyle={{ fontSize: 11 }} /></PieChart></ResponsiveContainer></div>;
}

export function ReportTrendChart({ weeks }) {
  return <div className="chart-box" data-testid="report-trend-chart"><ResponsiveContainer width="100%" height={220}>
    <BarChart data={weeks} margin={{ right: 8 }}><CartesianGrid vertical={false} stroke="#eef2f7" /><XAxis dataKey="week" tick={tick} /><YAxis allowDecimals={false} tick={tick} width={24} />
      <Tooltip {...tip} /><Legend iconType="square" wrapperStyle={{ fontSize: 11 }} />
      <Bar dataKey="Daily" stackId="r" fill="#2563eb" barSize={18} /><Bar dataKey="Weekly" stackId="r" fill="#d97706" barSize={18} /></BarChart></ResponsiveContainer></div>;
}
