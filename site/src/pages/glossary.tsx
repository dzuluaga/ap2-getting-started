import React from 'react';
import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import {glossary} from '@site/src/data/glossary';

export default function Glossary(): ReactNode {
  const sorted = [...glossary].sort((a, b) => a.term.localeCompare(b.term));
  return (
    <Layout title="Glossary" description="AP2 terminology">
      <main className="container margin-vert--lg">
        <h1>AP2 Glossary</h1>
        <p>The vocabulary used across the lessons. Say it like you mean it.</p>
        <table>
          <thead>
            <tr><th>Term</th><th>Plain English</th><th>Closer to spec</th></tr>
          </thead>
          <tbody>
            {sorted.map((e) => (
              <tr key={e.id} id={e.id}>
                <td><strong>{e.term}</strong>{e.acronym ? ` (${e.acronym})` : ''}</td>
                <td>{e.short}</td>
                <td>{e.spec}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </Layout>
  );
}
