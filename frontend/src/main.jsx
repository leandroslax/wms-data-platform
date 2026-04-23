import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { marked } from "marked";
import "./styles.css";

const QUICK_QUESTIONS = [
  "Quantos pedidos existem na gold?",
  "Como está o SLA de entrega dos pedidos?",
  "Quais produtos têm maior risco de ruptura de estoque?",
  "Qual o desempenho dos operadores esta semana?"
];

const DASHBOARDS = [
  {
    name: "Grafana Operações",
    href: "http://localhost:3000/d/wms-operations",
    caption: "KPIs, SLA, estoque e movimentações"
  },
  {
    name: "Superset WMS",
    href: "http://localhost:8088/superset/dashboard/wms-operations",
    caption: "Visão analítica operacional"
  },
  {
    name: "LangFuse Agents",
    href: "http://localhost:3001/project/wms-agents",
    caption: "Traces, tokens e qualidade das respostas"
  }
];

function App() {
  const [metrics, setMetrics] = useState([]);
  const [health, setHealth] = useState("checking");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Olá. Eu sou a interface dos agentes WMS. Faça uma pergunta operacional ou use os atalhos ao lado para começar."
    }
  ]);
  const [question, setQuestion] = useState("");
  const [progress, setProgress] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    loadMetrics();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, progress]);

  async function loadMetrics() {
    const fetchJson = async (path) => {
      const res = await fetch(path);
      if (!res.ok) throw new Error(`${path}: ${res.status}`);
      return res.json();
    };

    try {
      const [healthData, orders, movements, inventory] = await Promise.all([
        fetchJson("/health"),
        fetchJson("/orders/summary"),
        fetchJson("/movements/summary"),
        fetchJson("/inventory/snapshot")
      ]);

      setHealth(healthData.status === "ok" ? "online" : "degraded");
      setMetrics([
        { label: "Pedidos", value: formatNumber(orders.total_orders), hint: "gold.mart_order_sla" },
        { label: "Movimentos", value: formatNumber(movements.total_movements), hint: "gold.fct_movements" },
        { label: "SKUs", value: formatNumber(inventory.total_skus), hint: "snapshot atual" },
        { label: "Disponível", value: formatNumber(inventory.total_available_qty), hint: "saldo em estoque" }
      ]);
    } catch (error) {
      setHealth("degraded");
      setMetrics([
        { label: "API", value: "offline", hint: error.message },
        { label: "Pedidos", value: "--", hint: "aguardando backend" },
        { label: "Movimentos", value: "--", hint: "aguardando backend" },
        { label: "SKUs", value: "--", hint: "aguardando backend" }
      ]);
    }
  }

  async function sendMessage(event, explicitQuestion) {
    event?.preventDefault();
    const prompt = (explicitQuestion ?? question).trim();
    if (!prompt || isStreaming) return;

    setQuestion("");
    setMessages((current) => [...current, { role: "user", content: prompt }]);
    setProgress([{ agent: "Crew", message: "Iniciando agentes WMS..." }]);
    setIsStreaming(true);

    try {
      const res = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt })
      });

      if (!res.ok || !res.body) {
        const detail = await safeError(res);
        throw new Error(detail);
      }

      await readSseStream(res.body, (eventData) => {
        if (eventData.type === "progress") {
          setProgress((current) => [
            ...current,
            { agent: eventData.agent, message: eventData.message }
          ]);
        }

        if (eventData.type === "done") {
          setMessages((current) => [
            ...current,
            { role: "assistant", content: eventData.answer, markdown: true }
          ]);
          setProgress([]);
        }

        if (eventData.type === "error") {
          throw new Error(eventData.message);
        }
      });
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: `Falha ao consultar agentes: ${error.message}` }
      ]);
      setProgress([]);
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">WMS Data Platform</p>
          <h1>Centro operacional com agentes, dados e observabilidade.</h1>
          <p className="lead">
            Pergunte em linguagem natural, acompanhe o progresso dos agentes em streaming
            e abra os dashboards locais sem sair do fluxo.
          </p>
        </div>
        <div className={`status-card ${health}`}>
          <span>{health === "online" ? "API online" : "API degradada"}</span>
          <button type="button" onClick={loadMetrics}>Atualizar métricas</button>
        </div>
      </section>

      <section className="metrics-grid" aria-label="Resumo operacional">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.hint}</small>
          </article>
        ))}
      </section>

      <section className="workspace">
        <aside className="side-panel">
          <div className="panel-block">
            <h2>Perguntas rápidas</h2>
            {QUICK_QUESTIONS.map((item) => (
              <button
                className="quick-question"
                type="button"
                disabled={isStreaming}
                key={item}
                onClick={(event) => sendMessage(event, item)}
              >
                {item}
              </button>
            ))}
          </div>

          <div className="panel-block">
            <h2>Dashboards</h2>
            {DASHBOARDS.map((dashboard) => (
              <a className="dashboard-link" href={dashboard.href} target="_blank" rel="noreferrer" key={dashboard.name}>
                <strong>{dashboard.name}</strong>
                <span>{dashboard.caption}</span>
              </a>
            ))}
          </div>
        </aside>

        <section className="chat-card" aria-label="Chat dos agentes WMS">
          <div className="chat-header">
            <div>
              <h2>ChatInterface</h2>
              <span>AnalystAgent + ResearchAgent + ReporterAgent</span>
            </div>
            {isStreaming && <div className="pulse">streaming SSE</div>}
          </div>

          <div className="messages">
            {messages.map((message, index) => (
              <Message message={message} key={`${message.role}-${index}`} />
            ))}
            {progress.length > 0 && <ProgressLog progress={progress} />}
            <div ref={bottomRef} />
          </div>

          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={question}
              disabled={isStreaming}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  sendMessage(event);
                }
              }}
              placeholder="Ex.: Quais pedidos estão fora do SLA?"
              rows={2}
            />
            <button type="submit" disabled={isStreaming || !question.trim()}>
              {isStreaming ? "Aguardando..." : "Enviar"}
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function Message({ message }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="avatar">{message.role === "user" ? "LS" : "AI"}</div>
      <div
        className="bubble"
        dangerouslySetInnerHTML={
          message.markdown
            ? { __html: marked.parse(message.content) }
            : undefined
        }
      >
        {!message.markdown ? message.content : null}
      </div>
    </article>
  );
}

function ProgressLog({ progress }) {
  return (
    <article className="message assistant">
      <div className="avatar">AI</div>
      <div className="bubble progress">
        <div className="loader" />
        {progress.slice(-6).map((item, index) => (
          <p key={`${item.agent}-${index}`}>
            <strong>{item.agent}</strong>
            <span>{item.message}</span>
          </p>
        ))}
      </div>
    </article>
  );
}

async function readSseStream(body, onEvent) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      onEvent(JSON.parse(line.replace("data: ", "")));
    }
  }
}

async function safeError(res) {
  try {
    const json = await res.json();
    return json.detail ?? `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

createRoot(document.getElementById("root")).render(<App />);
