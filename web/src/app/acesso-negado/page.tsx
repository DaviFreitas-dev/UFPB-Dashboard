import Link from "next/link";

import styles from "@/components/auth-shell.module.css";

export default function AccessDeniedPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <span className={styles.brand}>NEXO</span>
        <h1>Acesso não autorizado</h1>
        <p>Esta conta não tem acesso ao NEXO.</p>
        <Link href="/entrar">Voltar ao login</Link>
      </section>
    </main>
  );
}
