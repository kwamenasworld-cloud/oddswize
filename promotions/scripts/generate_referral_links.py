import argparse
import csv
import hashlib
import re
import secrets
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


def slugify(value):
    value = value.strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip('-')
    return value


def make_code(label):
    label = label.strip()
    base = slugify(label)
    digest = hashlib.sha1(label.encode('utf-8')).hexdigest()[:6]
    if base:
        return f'{base[:10]}-{digest}'
    return digest


def make_random_code():
    return secrets.token_hex(3)


def append_params(base_url, params):
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    for key, value in params.items():
        query[key] = [value]
    flat = urlencode({k: v[0] for k, v in query.items()})
    return urlunparse(parsed._replace(query=flat))


def load_labels(args):
    labels = []
    if args.names:
        labels.extend([name.strip() for name in args.names.split(',') if name.strip()])
    if args.file:
        for line in Path(args.file).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            labels.append(line)
    if not labels and args.count:
        labels = [f'member-{idx + 1}' for idx in range(args.count)]
    return labels


def main():
    parser = argparse.ArgumentParser(description='Generate referral links with tracking params.')
    parser.add_argument('--base-url', default='https://oddswize.com/odds')
    parser.add_argument('--names', help='Comma-separated list of names/handles')
    parser.add_argument('--file', help='File with one name per line')
    parser.add_argument('--count', type=int, help='Generate N generic codes')
    parser.add_argument('--campaign', default='community')
    parser.add_argument('--source', default='referral')
    parser.add_argument('--medium', default='share')
    parser.add_argument('--out', default='promotions/output/referral_links.csv')

    args = parser.parse_args()

    labels = load_labels(args)
    if not labels:
        raise SystemExit('Provide --names, --file, or --count to generate referral links.')

    rows = []
    for label in labels:
        code = make_code(label)
        url = append_params(args.base_url, {
            'ref': code,
            'utm_source': args.source,
            'utm_medium': args.medium,
            'utm_campaign': args.campaign,
        })
        rows.append((label, code, url))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.out).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['label', 'code', 'url'])
        writer.writerows(rows)

    print(f'Wrote {len(rows)} referral links to {args.out}')


if __name__ == '__main__':
    main()
