import type { Route } from "next";
import Link from "next/link";
import {
  Award,
  BookOpen,
  ChartNoAxesCombined,
  CheckSquare2,
  Dumbbell,
  ListTodo,
  Settings,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";

import styles from "./more-dashboard.module.css";

type MoreItem = {
  href: Route;
  label: string;
  detail: string;
  icon: LucideIcon;
};

const items: MoreItem[] = [
  { href: "/ciclo", label: "Ciclo", detail: "Carga e saldo por disciplina", icon: Target },
  { href: "/missoes", label: "Missões", detail: "Escolha o próximo bloco", icon: Sparkles },
  { href: "/leitura", label: "Leitura", detail: "Livros e metas de páginas", icon: BookOpen },
  { href: "/tarefas", label: "Tarefas", detail: "Pendências organizadas por dia", icon: CheckSquare2 },
  { href: "/habitos", label: "Hábitos", detail: "Ritmo diário e sequências", icon: ListTodo },
  { href: "/atividade", label: "Atividade", detail: "Movimento registrado no dia", icon: Dumbbell },
  { href: "/progresso", label: "Progresso", detail: "Horas, questões e desempenho", icon: ChartNoAxesCombined },
  { href: "/conquistas", label: "Conquistas", detail: "Marcos alcançados", icon: Award },
  { href: "/configuracoes", label: "Configurações", detail: "Disciplinas e carga do ciclo", icon: Settings },
];

export function MoreDashboard() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <p>Áreas do NEXO</p>
        <h1>Mais</h1>
        <span>Acesse as áreas que ficam fora da navegação rápida.</span>
      </header>

      <nav className={styles.grid} aria-label="Outras áreas do NEXO">
        {items.map(({ href, label, detail, icon: Icon }) => (
          <Link className={styles.card} href={href} key={href}>
            <span className={styles.icon}>
              <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
            </span>
            <span>
              <strong>{label}</strong>
              <small>{detail}</small>
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
