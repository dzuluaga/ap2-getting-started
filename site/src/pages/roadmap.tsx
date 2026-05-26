import React from 'react';
import type {ReactNode} from 'react';
import Layout from '@theme/Layout';

type Lesson = {n: string; title: string; v1: boolean};

const lessons: Lesson[] = [
  {n: '00', title: 'Why agent payments?', v1: true},
  {n: '01', title: 'The cast & the journeys', v1: true},
  {n: '02', title: 'Mandates, the unit of trust', v1: true},
  {n: '03', title: 'Selective disclosure: SD-JWT & key binding', v1: true},
  {n: '04', title: 'Mandate chains & receipts; SCA & dynamic linking', v1: false},
  {n: '05', title: 'Human-Present happy path, end-to-end', v1: false},
  {n: '06', title: 'Human-Not-Present & autonomous delegation', v1: false},
  {n: '07', title: 'Riding on A2A', v1: false},
  {n: '08', title: 'AP2 with MCP, UCP, and x402', v1: false},
  {n: '09', title: 'Action authorization, disputes & liability', v1: false},
];

export default function Roadmap(): ReactNode {
  return (
    <Layout title="Roadmap" description="The AP2 learning path">
      <main className="container margin-vert--lg">
        <h1>Roadmap</h1>
        <p>Lessons ship incrementally. v1 covers the foundations (00–02).</p>
        <ul>
          {lessons.map((l) => (
            <li key={l.n}>
              <strong>{l.n}</strong> — {l.title}{' '}
              {l.v1 ? <span>✅ available</span> : <em>· coming soon</em>}
            </li>
          ))}
        </ul>
      </main>
    </Layout>
  );
}
