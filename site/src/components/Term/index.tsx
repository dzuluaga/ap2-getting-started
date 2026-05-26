import React from 'react';
import type {ReactNode} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import {glossary} from '@site/src/data/glossary';

export default function Term({id, children}: {id: string; children: ReactNode}): ReactNode {
  const entry = glossary.find((e) => e.id === id);
  // Use useBaseUrl so the href respects `baseUrl` (the site lives at /ap2/),
  // not the apex. Raw <a> doesn't auto-prefix the way <Link to=...> does.
  const href = `${useBaseUrl('/glossary')}#${id}`;
  return (
    <a href={href} title={entry ? entry.short : id}
       style={{textDecoration: 'underline dotted', cursor: 'help'}}>
      {children}
    </a>
  );
}
