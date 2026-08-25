import { signIn } from "@/auth";
import styles from "@/components/auth-shell.module.css";

export default function SignInPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <span className={styles.brand}>NEXO</span>
        <h1>Acesso pessoal</h1>
        <p>Entre com sua conta GitHub para abrir o NEXO.</p>
        <form
          action={async () => {
            "use server";
            await signIn("github", { redirectTo: "/" });
          }}
        >
          <button type="submit">Entrar com GitHub</button>
        </form>
      </section>
    </main>
  );
}
