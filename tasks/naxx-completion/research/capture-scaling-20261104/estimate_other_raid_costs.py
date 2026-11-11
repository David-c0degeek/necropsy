from pathlib import Path
import json,hashlib,collections
from necropsy.snapshot.archive import VerifiedArchive,load_entries_manifest
from necropsy.wcl.derive import source_actor_ids,project_pages,SOURCE_RULE,CRITICAL_RULE,DerivationUnsupported
from necropsy.wcl.acquire import fight_pets
root=Path.cwd()
specs=json.loads((root/'tests/golden/raids/provenance.json').read_bytes())['fixtures']
labels=('mc-holy-paladin-raid-context','mc-holy-raid-context','mc-restoration-shaman-raid-context','bwl-holy-raid-context','aq40-holy-complete-context','aq40-hunter-cohort-context')
results=[]
for label in labels:
 spec=next(f for f in specs if f['label']==label)
 path=root/'tests/golden/raids'/spec['archive']
 with VerifiedArchive(path,expected_sha256=spec['sha256'],entries=load_entries_manifest(path.with_suffix('.entries'))) as z:
  m=z.read_json('necropsy-snapshot.json'); names=z.names(); count=collections.Counter()
  whole={}
  for proof in m['encounter_streams']:
   if proof['role']!='encounter':continue
   prefix=f"events/{proof['report']}/fight_{proof['fight']}/encounter/all_"
   whole[proof['report'],proof['fight']]=[z.read_bytes(n) for n in sorted(names) if n.startswith(prefix)]
  for proof in [*m['streams'],*m['encounter_streams']]:
   code,fid,role,direction=proof['report'],proof['fight'],proof['role'],proof['direction']
   count['current_event_pages']+=len(proof['pages'])
   if role=='encounter': count['all_pages']+=len(proof['pages']);continue
   parent_bytes=whole[code,fid]; pages=[json.loads(p) for p in parent_bytes]
   prefix=f'events/{code}/fight_{fid}/'
   if role=='critical':
    selected=sorted(n for n in names if n.startswith(prefix+'encounter/critical_'))
   else:
    selected=sorted(n for n in names if n.startswith(prefix+f'{role}_{proof["actor_id"]}_') and '/'+direction+'_' in n)
   actual=[z.read_bytes(n) for n in selected]
   flat_actual=[e for p in actual for e in json.loads(p)['data']]
   if direction=='target':
    count['target_scopes']+=1
    count['target_exact_parent_bytes']+=actual==parent_bytes
    count['target_events_equal_all']+=flat_actual==[e for p in pages for e in p['data']]
   else:
    try:
     if role=='critical': projected=project_pages(pages,CRITICAL_RULE)
     else:
      report=z.read_json(f'reports/{code}/fight_{fid}.json')['report']
      ids=source_actor_ids(report,fid,proof['actor_id'])
      projected=project_pages(pages,SOURCE_RULE,actor_ids=ids)
      actors={a['id']:a for a in report['masterData']['actors']}
      owners={a['id']:a.get('petOwner') for a in actors.values()}
      owners.update({p['id']:p['petOwner'] for p in report['fights'][0]['friendlyPets'] if p.get('petOwner')})
      actor=proof['actor_id']
      while owners[actor] is not None: actor=owners[actor]
      if fight_pets(report,report['fights'][0],actor)[0] is None: raise DerivationUnsupported('incomplete ownership')
    except DerivationUnsupported:
     count[role+'_unsupported']+=1
     count['fallback_pages']+=len(proof['pages'])
    else:
     equal=flat_actual==[e for p in projected for e in p['data']]
     count[role+'_ordered_equal']+=equal
     count[role+'_mismatch']+=not equal
  results.append({'label':label,'path':path.relative_to(root).as_posix(),'sha256':spec['sha256'],'zone':m['zone']['id'],'bosses':len(m['bosses']),'fights':len(m['fights']),'actors':sum(len(f['participants']) for f in m['fights']),'reports':len(m['report_sets']),'counts':dict(count)})
  print(label,dict(count),flush=True)
out=root/'tasks/naxx-completion/research/capture-scaling-20261104/other-raid-costs.json'
out.write_text(json.dumps({'kind':'Offline historical page/projection audit; no API queries, activation, acquisition or acceptance','samples':results,'scope':{'configurations_per_raid':34,'comparison_depth':3,'actors_per_cell_including_subject':4,'bosses':{'aq40':9,'bwl':9,'mc':10},'bwl_note':'Includes separate Ebonroc, Flamegor and combined Ebonroc/Flamegor ranking encounters.'}},indent=2)+'\n',encoding='utf-8')
