import type { ReactNode } from "react";
import {
  Activity,
  Award,
  BookOpen,
  CalendarDays,
  ChartNoAxesCombined,
  CheckSquare2,
  CircleGauge,
  Dumbbell,
  ListTodo,
  NotebookTabs,
  Settings,
  Sparkles,
  Target,
} from "lucide-react";

import type { DashboardUser } from "@/lib/dashboard";
import { ratio } from "@/lib/dashboard";
import styles from "./app-shell.module.css";

const navigation = [
  { label: "Hoje", icon: CircleGauge, active: true },
  { label: "Planejar", icon: CalendarDays },
  { label: "Rotina", icon: NotebookTabs },
  { label: "Ciclo", icon: Target },
  { label: "Missões", icon: Sparkles },
  { label: "Leitura", icon: BookOpen },
  { label: "Tarefas", icon: CheckSquare2 },
  { label: "Hábitos", icon: ListTodo },
  { label: "Atividade", icon: Dumbbell },
  { label: "Progresso", icon: ChartNoAxesCombined },
  { label: "Conquistas", icon: Award },
  { label: "Configurações", icon: Settings },
];

const mobileNavigation = navigation.filter(({ label }) =>
  ["Hoje", "Planejar", "Missões", "Progresso"].includes(label),
);

type AppShellProps = {
  children: ReactNode;
  user: DashboardUser;
};

export function AppShell({ children, user }: AppShellProps) {
  const levelProgress = ratio(user.xp, user.nextLevelXp);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>N</span>
          <span className={styles.brandName}>NEXO</span>
        </div>

        <section className={styles.levelCard} aria-label="Progresso de nível">
          <div className={styles.levelRow}>
            <strong>Nível {user.level}</strong>
            <span>{user.xp.toLocaleString("pt-BR")} XP</span>
          </div>
          <div className={styles.levelTrack} aria-hidden="true">
            <span style={{ width: `${levelProgress * 100}%` }} />
          </div>
          <small>{user.nextLevelXp.toLocaleString("pt-BR")} XP para o próximo nível</small>
        </section>

        <nav className={styles.navigation} aria-label="Navegação principal">
          {navigation.map(({ label, icon: Icon, active }) => (
            <button
              aria-current={active ? "page" : undefined}
              className={active ? styles.navItemActive : styles.navItem}
              disabled={!active}
              key={label}
              title={active ? undefined : "Disponível no aplicativo atual"}
              type="button"
            >
              <Icon aria-hidden="true" size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className={styles.migrationNote}>
          <Activity aria-hidden="true" size={15} />
          <span>Interface em migração gradual</span>
        </div>
      </aside>

      <main className={styles.main}>{children}</main>

      <nav className={styles.mobileNav} aria-label="Navegação móvel">
        {mobileNavigation.map(({ label, icon: Icon, active }) => (
          <button
            aria-current={active ? "page" : undefined}
            className={active ? styles.mobileItemActive : styles.mobileItem}
            disabled={!active}
            key={label}
            type="button"
          >
            <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
            <span>{label}</span>
          </button>
        ))}
        <button className={styles.mobileItem} disabled type="button">
          <Settings aria-hidden="true" size={20} strokeWidth={1.8} />
          <span>Mais</span>
        </button>
      </nav>
    </div>
  );
}
