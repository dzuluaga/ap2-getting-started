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
        <div style={{maxWidth: 720, margin: '0 auto 2.5rem'}}>
          <div style={{position: 'relative', paddingTop: '56.25%'}}>
            <iframe
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                border: 0,
                borderRadius: 8,
              }}
              src="https://www.youtube-nocookie.com/embed/jSHj0z9Gi24"
              title="Intro to the Agent Payments Protocol (AP2)"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          </div>
          <p style={{textAlign: 'center', marginTop: '0.75rem', opacity: 0.8}}>
            A short intro to the Agent Payments Protocol.
          </p>
        </div>
        <p>
          A public, incremental learning resource. Each lesson follows the same
          spine: <strong>Frame · Build · Map · Inspect · Check</strong>. Every
          code snippet here is real, tested code from the repo.
        </p>
        <p>
          New here? See the <Link to="/roadmap">roadmap</Link>, skim the{' '}
          <Link to="/glossary">glossary</Link>, or jump to the{' '}
          <Link to="/vision">end vision</Link>.
        </p>
      </main>
    </Layout>
  );
}
