"""
Deterministic IMDRF mapping with Groq fallback (Annex-controlled).
"""
import json
import os
import pandas as pd
import re
from typing import Dict, Optional
from backend.groq_client import GroqClient


class IMDRFMapper:
    """Maps Device Problem to IMDRF codes using deterministic matching with Groq fallback."""
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        self.groq_client = groq_client or GroqClient()
        self.level1_map = {}
        self.level2_map = {}
        self.level3_map = {}
        self.level1_terms = []  # For Groq fallback
        self.level2_hierarchy = {}  # level1_term -> [level2_terms]
        self.level3_hierarchy = {}  # level2_term -> [level3_terms]
        # Use /tmp on Vercel (serverless) or cache/ for local
        self.cache_dir = os.path.join(os.getenv('TMPDIR', os.getenv('TMP', 'cache')), 'maude_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "device_problem_to_imdrf_cache.json")
        self.cache = self._load_cache()
        self.annex_codes = set()  # All valid codes for validation
    
    def _load_cache(self) -> dict:
        """Load IMDRF mapping cache."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save IMDRF mapping cache."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save IMDRF cache: {e}")
    
    def _norm_term(self, s: str) -> str:
        """Deterministic normalization for matching only."""
        if s is None:
            return ""
        s = str(s).strip().lower()
        if not s or s == "nan":
            return ""
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"\s*/\s*", "/", s)
        s = re.sub(r"[.,;:]+$", "", s).strip()
        return s
    
    def _is_blank(self, x) -> bool:
        if x is None:
            return True
        s = str(x).strip()
        return (s == "") or (s.lower() == "nan")
    
    def load_annex(self, annex_xlsx_path: str):
        """Load Annex structure deterministically."""
        xl = pd.ExcelFile(annex_xlsx_path)
        
        level1_map, level2_map, level3_map = {}, {}, {}
        level1_terms = []
        level2_hierarchy = {}
        level3_hierarchy = {}
        annex_codes = set()
        
        required_cols = {"Level 1 Term", "Level 2 Term", "Level 3 Term", "Code"}
        
        for sheet in xl.sheet_names:
            df_raw = xl.parse(sheet_name=sheet, header=None, dtype=str)
            
            # Find header row
            header_row_idx = None
            for i in range(min(50, len(df_raw))):
                row_vals = [str(v).strip() for v in df_raw.iloc[i].tolist()]
                if "Level 1 Term" in row_vals:
                    header_row_idx = i
                    break
            if header_row_idx is None:
                continue
            
            df = xl.parse(sheet_name=sheet, header=header_row_idx, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            
            if not required_cols.issubset(set(df.columns)):
                continue
            
            # Forward fill
            df["Level 1 Term"] = df["Level 1 Term"].ffill()
            df["Level 2 Term"] = df["Level 2 Term"].ffill()
            
            current_l1 = None
            current_l2 = None
            
            for _, r in df.iterrows():
                code = "" if r.get("Code") is None else str(r.get("Code")).strip()
                if not code or code.lower() == "nan":
                    continue
                
                annex_codes.add(code)
                
                l1 = self._norm_term(r.get("Level 1 Term"))
                l2 = self._norm_term(r.get("Level 2 Term"))
                l3 = self._norm_term(r.get("Level 3 Term"))
                
                if len(code) == 3 and l1:
                    level1_map.setdefault(l1, code)
                    if l1 not in level1_terms:
                        level1_terms.append(l1)
                    current_l1 = l1
                elif len(code) == 5 and l2:
                    level2_map.setdefault(l2, code)
                    if current_l1:
                        if current_l1 not in level2_hierarchy:
                            level2_hierarchy[current_l1] = []
                        if l2 not in level2_hierarchy[current_l1]:
                            level2_hierarchy[current_l1].append(l2)
                    current_l2 = l2
                elif len(code) == 7 and l3:
                    level3_map.setdefault(l3, code)
                    if current_l2:
                        if current_l2 not in level3_hierarchy:
                            level3_hierarchy[current_l2] = []
                        if l3 not in level3_hierarchy[current_l2]:
                            level3_hierarchy[current_l2].append(l3)
        
        self.level1_map = level1_map
        self.level2_map = level2_map
        self.level3_map = level3_map
        self.level1_terms = level1_terms
        self.level2_hierarchy = level2_hierarchy
        self.level3_hierarchy = level3_hierarchy
        self.annex_codes = annex_codes
        
        print(f"Loaded Annex: L1={len(level1_map)}, L2={len(level2_map)}, L3={len(level3_map)}, Total codes={len(annex_codes)}")
    
    def _deterministic_map(self, device_problem_part: str) -> str:
        """Deterministic mapping for a single part."""
        if self._is_blank(device_problem_part):
            return ""
        
        raw = str(device_problem_part).strip()
        if not raw:
            return ""
        
        if self._norm_term(raw) == self._norm_term("Appropriate Term/Code Not Available"):
            return ""
        
        pn = self._norm_term(raw)
        if not pn:
            return ""
        
        # Check cache first
        if pn in self.cache:
            return self.cache[pn]
        
        # Try deterministic matching
        code = None
        if pn in self.level3_map:
            code = self.level3_map[pn]
        elif pn in self.level2_map:
            code = self.level2_map[pn]
        elif pn in self.level1_map:
            code = self.level1_map[pn]
        
        # Cache result (even if blank)
        self.cache[pn] = code if code else ""
        self._save_cache()
        
        return code if code else ""
    
    def _groq_fallback_level1(self, device_problem_part: str) -> Optional[str]:
        """Groq fallback for Level-1 selection (Annex-controlled)."""
        terms_str = ', '.join([f'"{t}"' for t in self.level1_terms[:100]])  # Limit to avoid token limits
        
        prompt = f"""You are selecting the most appropriate Level-1 IMDRF term for a device problem.

Device Problem: "{device_problem_part}"

Available Level-1 terms (from Annex, you MUST select exactly one from this list):
{terms_str}

CRITICAL RULES:
- Return ONLY valid JSON
- Select the EXACT term from the list above that best matches the device problem
- If no good match, return {{"selected": "NO_MATCH"}}
- Do NOT modify or paraphrase the term

Return format (JSON only):
{{"selected": "<exact term from list>"}} OR {{"selected": "NO_MATCH"}}"""

        try:
            response = self.groq_client.client.chat.completions.create(
                model=self.groq_client.model,
                messages=[
                    {"role": "system", "content": "You are an IMDRF coding expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            selected = result.get("selected", "NO_MATCH")
            
            if selected == "NO_MATCH":
                return None
            
            # Validate: must be in level1_terms
            selected_norm = self._norm_term(selected)
            if selected_norm in self.level1_map:
                return self.level1_map[selected_norm]
            
            return None
            
        except Exception as e:
            print(f"Warning: Groq Level-1 selection failed: {e}")
            return None
    
    def _groq_fallback_level2(self, device_problem_part: str, level1_term: str) -> Optional[str]:
        """Groq fallback for Level-2 selection (Annex-controlled)."""
        level2_terms = self.level2_hierarchy.get(level1_term, [])
        if not level2_terms:
            return None
        
        terms_str = ', '.join([f'"{t}"' for t in level2_terms[:50]])
        
        prompt = f"""You are selecting the most appropriate Level-2 IMDRF term for a device problem.

Device Problem: "{device_problem_part}"
Level-1 context: "{level1_term}"

Available Level-2 terms (under Level-1, you MUST select exactly one from this list):
{terms_str}

CRITICAL RULES:
- Return ONLY valid JSON
- Select the EXACT term from the list above
- If no good match, return {{"selected": "NO_MATCH"}}

Return format (JSON only):
{{"selected": "<exact term>"}} OR {{"selected": "NO_MATCH"}}"""

        try:
            response = self.groq_client.client.chat.completions.create(
                model=self.groq_client.model,
                messages=[
                    {"role": "system", "content": "You are an IMDRF coding expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            selected = result.get("selected", "NO_MATCH")
            
            if selected == "NO_MATCH":
                return None
            
            selected_norm = self._norm_term(selected)
            if selected_norm in self.level2_map:
                return self.level2_map[selected_norm]
            
            return None
            
        except Exception as e:
            print(f"Warning: Groq Level-2 selection failed: {e}")
            return None
    
    def _groq_fallback_level3(self, device_problem_part: str, level2_term: str) -> Optional[str]:
        """Groq fallback for Level-3 selection (Annex-controlled)."""
        level3_terms = self.level3_hierarchy.get(level2_term, [])
        if not level3_terms:
            return None
        
        terms_str = ', '.join([f'"{t}"' for t in level3_terms[:50]])
        
        prompt = f"""You are selecting the most appropriate Level-3 IMDRF term for a device problem.

Device Problem: "{device_problem_part}"
Level-2 context: "{level2_term}"

Available Level-3 terms (under Level-2, you MUST select exactly one from this list):
{terms_str}

CRITICAL RULES:
- Return ONLY valid JSON
- Select the EXACT term from the list above
- If no good match, return {{"selected": "NO_MATCH"}}

Return format (JSON only):
{{"selected": "<exact term>"}} OR {{"selected": "NO_MATCH"}}"""

        try:
            response = self.groq_client.client.chat.completions.create(
                model=self.groq_client.model,
                messages=[
                    {"role": "system", "content": "You are an IMDRF coding expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            selected = result.get("selected", "NO_MATCH")
            
            if selected == "NO_MATCH":
                return None
            
            selected_norm = self._norm_term(selected)
            if selected_norm in self.level3_map:
                return self.level3_map[selected_norm]
            
            return None
            
        except Exception as e:
            print(f"Warning: Groq Level-3 selection failed: {e}")
            return None
    
    def _groq_fallback(self, device_problem_part: str) -> str:
        """Groq fallback hierarchical selection (Annex-controlled)."""
        pn = self._norm_term(device_problem_part)
        if not pn:
            return ""
        
        # Try Level-1
        l1_code = self._groq_fallback_level1(device_problem_part)
        if not l1_code:
            return ""
        
        # Try Level-2
        l1_term_norm = None
        for term, code in self.level1_map.items():
            if code == l1_code:
                l1_term_norm = term
                break
        
        if not l1_term_norm:
            return l1_code  # Return Level-1 code
        
        l2_code = self._groq_fallback_level2(device_problem_part, l1_term_norm)
        if not l2_code:
            return l1_code  # Return Level-1 code
        
        # Try Level-3
        l2_term_norm = None
        for term, code in self.level2_map.items():
            if code == l2_code:
                l2_term_norm = term
                break
        
        if not l2_term_norm:
            return l2_code  # Return Level-2 code
        
        l3_code = self._groq_fallback_level3(device_problem_part, l2_term_norm)
        if l3_code:
            return l3_code  # Return Level-3 code
        
        return l2_code  # Return Level-2 code
    
    def map_device_problem(self, device_problem_value: str) -> str:
        """
        Map Device Problem to IMDRF code.
        Uses deterministic matching first, Groq fallback if needed.
        """
        if self._is_blank(device_problem_value):
            return ""
        
        raw = str(device_problem_value).strip()
        if not raw:
            return ""
        
        if self._norm_term(raw) == self._norm_term("Appropriate Term/Code Not Available"):
            return ""
        
        # Split on semicolons
        parts = [p.strip() for p in raw.split(";")]
        codes = []
        
        for p in parts:
            if self._is_blank(p):
                continue
            
            # Try deterministic first
            code = self._deterministic_map(p)
            
            # Groq fallback if deterministic failed
            if not code:
                pn = self._norm_term(p)
                # Only use Groq if not in cache (to avoid repeated calls)
                if pn and pn not in self.cache:
                    code = self._groq_fallback(p)
                    # Cache the result
                    self.cache[pn] = code
                    self._save_cache()
            
            if code:
                codes.append(code)
        
        if not codes:
            return ""
        
        # Choose deepest code (len 7 > 5 > 3), tie-breaker lexicographically smallest
        codes_sorted = sorted(codes, key=lambda c: (-len(c), c))
        return codes_sorted[0]
    
    def validate_code(self, code: str) -> bool:
        """Validate that code exists in Annex."""
        return code in self.annex_codes
