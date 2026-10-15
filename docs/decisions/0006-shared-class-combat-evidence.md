# Shared class combat evidence and ranking categories

Status: accepted engineering contract; domain/product acceptance is separate.

All nine Classic Era classes share the existing pipeline. Hunter and Druid keep
their existing class contracts; remaining class plugins use common actor event,
total/coverage and role calculations with explicit per-class action sets. The
version1 analysis schema adds optional combat data rather than relabelling
another class's analysis as Druid. Shared class view, equipment, execution and
ability components render these records. No additional acquisition/cache/auth/
normalizer/publisher is introduced.

Ranking category, talent build and observed duty remain separate. The catalog
uses live verified ranking labels rather than localized gameData DPS/Healer names.
Unknown or unsupported filters are rejected. Role aliases resolve after class
resolution. Every class/category query retains its metric: healer roles use HPS,
tank categories use DPS metadata without treating it as survival or threat.
Source cast coverage governs absence/timing claims. Actor and owned-pet actions
are separate; missing listing/streams do not establish zero participation.

Record verification sources in class documentation; new category/action claims
need observed primary evidence and contract checks. Preserve immutable archives
and old saved Hunter rendering. Rollback is reverting additive adapters/contracts;
no destructive data migration occurs. Domain and product acceptance remain
separate from automated or agent engineering verification.
