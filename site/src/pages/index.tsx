import React from 'react';
import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home(): ReactNode {
  return (
    <Layout
      title="AP2 from First Principles"
      description="Learn the Agent Payments Protocol by building it, then mapping to the SDK.">
      <header className="hero hero--primary">
        <div className="container">
          <h1 className="hero__title">AP2 from First Principles</h1>
          <p className="hero__subtitle">
            Build the Agent Payments Protocol by hand — mandates, signing, roles,
            trust — then map every piece to the official SDK.
          </p>
          <div>
            <Link className="button button--secondary button--lg" to="/docs/why-agent-payments">
              Start with Lesson 00 →
            </Link>
          </div>
        </div>
      </header>
      <main className="container margin-vert--lg">
        <p>
          A public, incremental learning resource. Each lesson follows the same
          spine: <strong>Frame · Build · Map · Inspect · Check</strong>. Every
          code snippet here is real, tested code from the repo.
        </p>
        <p>
          New here? See the <Link to="/roadmap">roadmap</Link> or skim the{' '}
          <Link to="/glossary">glossary</Link>.
        </p>
      </main>
    </Layout>
  );
}
