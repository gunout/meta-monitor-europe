#!/usr/bin/env bash
HTML=~/Desktop/europa/frontend/index.html

echo "═══════════════════════════════════════════════════════════"
echo "  Vérification du fichier HTML"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "1. Taille :"
wc -c "$HTML"

echo ""
echo "2. Antislashs suspects (\\; \\, \\)) :"
grep -n '\\\\[;,]' "$HTML" || echo "   ✅ Aucun"

echo ""
echo "3. Ligne const API :"
grep -n "const API" "$HTML"

echo ""
echo "4. Fonction search :"
grep -n "function search" "$HTML"

echo ""
echo "5. Fermeture </script> :"
grep -n "</script>" "$HTML"

echo ""
echo "✅ Vérification terminée"
