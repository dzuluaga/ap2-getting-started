import React from 'react';
import type {ReactNode} from 'react';
import {glossary} from '@site/src/data/glossary';

export default function Term({id, children}: {id: string; children: ReactNode}): ReactNode {
  const entry = glossary.find((e) => e.id === id);
  return (
    <a href={`/glossary#${id}`} title={entry ? entry.short : id}
       style={{textDecoration: 'underline dotted', cursor: 'help'}}>
      {children}
    </a>
  );
}
