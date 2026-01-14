'use client';

import React from 'react';

interface ComparisonRow {
  feature: string;
  value1: string;
  value2: string;
}

interface ComparisonTableProps {
  product1Name: string;
  product2Name: string;
  rows: ComparisonRow[];
  recommendation?: string;
}

export function ComparisonTable({ product1Name, product2Name, rows, recommendation }: ComparisonTableProps) {
  // Shorten names for header
  const shortenName = (name: string, maxLen: number = 22) => {
    if (name.length <= maxLen) return name;
    return name.slice(0, maxLen - 3) + '...';
  };

  return (
    <div className="my-4">
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gradient-to-r from-red-500 to-red-600">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-bold text-white uppercase tracking-wider w-1/4">
                Feature
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-white uppercase tracking-wider w-[37.5%]">
                {shortenName(product1Name)}
              </th>
              <th className="px-4 py-3 text-left text-xs font-bold text-white uppercase tracking-wider w-[37.5%]">
                {shortenName(product2Name)}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {rows.map((row, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-4 py-3 text-sm font-semibold text-gray-900">
                  {row.feature}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {row.value1}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {row.value2}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {recommendation && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-gray-800">
            <span className="font-semibold text-green-700">💡 Recommendation:</span> {recommendation}
          </p>
        </div>
      )}
    </div>
  );
}

// Helper to detect and parse comparison content from message
export function parseComparisonFromMessage(content: string): {
  hasComparison: boolean;
  summaryText: string;
  comparison: { product1Name: string; product2Name: string; rows: ComparisonRow[] } | null;
  recommendation: string;
} {
  // Check if this looks like a comparison response
  if (!content.includes('Comparison Summary') || !content.includes(' vs ')) {
    return { hasComparison: false, summaryText: content, comparison: null, recommendation: '' };
  }

  const rows: ComparisonRow[] = [];
  let product1Name = 'Product 1';
  let product2Name = 'Product 2';
  let recommendation = '';

  // Split by lines
  const lines = content.split('\n');
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (!line) continue;
    
    // Check for recommendation section
    if (line.toLowerCase().startsWith('recommendation')) {
      // Collect all text after Recommendation:
      const colonIdx = line.indexOf(':');
      if (colonIdx > 0) {
        recommendation = line.slice(colonIdx + 1).trim();
      }
      // Also collect following lines as part of recommendation
      for (let j = i + 1; j < lines.length; j++) {
        const nextLine = lines[j].trim();
        if (nextLine && !nextLine.startsWith('•') && !nextLine.startsWith('-')) {
          recommendation += ' ' + nextLine;
        } else {
          break;
        }
      }
      continue;
    }
    
    // Check if line is a bullet point with " vs "
    if (!line.includes(' vs ')) continue;
    
    // Remove bullet prefix
    let cleanLine = line;
    if (line.startsWith('•') || line.startsWith('●') || line.startsWith('-') || line.startsWith('*')) {
      cleanLine = line.slice(1).trim();
    }
    
    // Find the FIRST colon (feature name ends there)
    const firstColonIdx = cleanLine.indexOf(':');
    if (firstColonIdx === -1) continue;
    
    const feature = cleanLine.slice(0, firstColonIdx).trim().replace(/\*\*/g, '');
    const restOfLine = cleanLine.slice(firstColonIdx + 1).trim();
    
    // Split by " vs "
    const vsIdx = restOfLine.indexOf(' vs ');
    if (vsIdx === -1) continue;
    
    let value1 = restOfLine.slice(0, vsIdx).trim();
    let value2 = restOfLine.slice(vsIdx + 4).trim();
    
    // Special handling for Price to extract product names
    if (feature.toLowerCase() === 'price') {
      // Pattern: "Product Name ($123.00)"
      const pricePattern = /^(.+?)\s*\(\$?([\d,.]+)\)$/;
      
      const match1 = value1.match(pricePattern);
      const match2 = value2.match(pricePattern);
      
      if (match1) {
        product1Name = match1[1].trim();
        value1 = '$' + match1[2];
      }
      if (match2) {
        product2Name = match2[1].trim();
        value2 = '$' + match2[2];
      }
    }
    
    rows.push({ feature, value1, value2 });
  }

  // Debug log
  console.log('[ComparisonTable] Parsed rows:', rows.length, rows);
  console.log('[ComparisonTable] Product names:', product1Name, product2Name);

  // Need at least 2 rows
  if (rows.length < 2) {
    console.log('[ComparisonTable] Not enough rows, showing as text');
    return { hasComparison: false, summaryText: content, comparison: null, recommendation: '' };
  }

  return {
    hasComparison: true,
    summaryText: 'Comparison Summary:',
    comparison: { product1Name, product2Name, rows },
    recommendation: recommendation.trim()
  };
}
