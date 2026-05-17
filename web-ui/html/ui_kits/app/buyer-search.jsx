// MeliSim — Buyer Search + Product Detail (real API)

function BuyerSearch() {
  const params = new URLSearchParams(location.search);
  const view = params.get('view'); // 'product' | null
  const productId = parseInt(params.get('id') || '0', 10);

  if (view === 'product' && productId > 0) return <ProductDetail id={productId} />;
  return <SearchResults />;
}

function SearchResults() {
  const params = new URLSearchParams(location.search);
  const initialQ = params.get('q') || '';
  const initialCat = params.get('category') || '';

  const [q, setQ] = React.useState(initialQ);
  const [category, setCategory] = React.useState(initialCat);
  const [minPrice, setMinPrice] = React.useState('');
  const [maxPrice, setMaxPrice] = React.useState('');

  const { data: searchData, loading: searchLoading, error: searchError } = useApi(
    () => MeliSim.search({ q, category: category || undefined, minPrice: minPrice || undefined, maxPrice: maxPrice || undefined }),
    [q, category, minPrice, maxPrice]
  );
  const { data: listData } = useApi(() => MeliSim.listProducts({ size: 50 }), []);

  // Fallback to local filter if Elasticsearch returns empty (warm-up race or
  // events haven't been consumed yet by search-service).
  const items = React.useMemo(() => {
    const fromSearch = searchData?.items || [];
    if (fromSearch.length > 0) return fromSearch;
    if (!listData?.items) return [];
    let r = listData.items;
    if (q) r = r.filter(p => (p.title || '').toLowerCase().includes(q.toLowerCase()) || (p.description || '').toLowerCase().includes(q.toLowerCase()));
    if (category) r = r.filter(p => p.category === category);
    if (minPrice) r = r.filter(p => Number(p.price) >= Number(minPrice));
    if (maxPrice) r = r.filter(p => Number(p.price) <= Number(maxPrice));
    return r;
  }, [searchData, listData, q, category, minPrice, maxPrice]);

  const categories = ['electronics', 'computers', 'home', 'fashion', 'audio', 'games', 'books', 'office', 'sports'];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '20px 16px', display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20, alignItems: 'start' }}>
      <Card hover={false} style={{ padding: 18, position: 'sticky', top: 110 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: C.gray800, marginBottom: 14 }}>Filtros</div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.gray700, marginBottom: 8 }}>Categoria</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
              <input type="radio" name="cat" checked={category === ''} onChange={() => setCategory('')} /> Todas
            </label>
            {categories.map(c => (
              <label key={c} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                <input type="radio" name="cat" checked={category === c} onChange={() => setCategory(c)} /> {c}
              </label>
            ))}
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.gray700, marginBottom: 8 }}>Faixa de preço</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <input type="number" placeholder="Min" value={minPrice} onChange={e => setMinPrice(e.target.value)} style={{ width: '50%', padding: '7px 9px', fontSize: 12, border: `1px solid ${C.gray200}`, borderRadius: 4, fontFamily: T.sans }} />
            <input type="number" placeholder="Max" value={maxPrice} onChange={e => setMaxPrice(e.target.value)} style={{ width: '50%', padding: '7px 9px', fontSize: 12, border: `1px solid ${C.gray200}`, borderRadius: 4, fontFamily: T.sans }} />
          </div>
        </div>
        <Btn variant="ghost" size="sm" onClick={() => { setQ(''); setCategory(''); setMinPrice(''); setMaxPrice(''); }}>Limpar filtros</Btn>
      </Card>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ fontSize: 14, color: C.gray700 }}>
            <strong style={{ color: C.gray900 }}>{searchLoading ? '…' : items.length}</strong> {items.length === 1 ? 'resultado' : 'resultados'}
            {q && <> para "<strong>{q}</strong>"</>}
            {category && <> em <strong>{category}</strong></>}
          </div>
        </div>

        {searchLoading && <Loading label="Buscando…" />}
        {searchError && !listData && <ErrorState error={searchError} />}
        {!searchLoading && items.length === 0 && (
          <EmptyState icon="🔍" title="Sem resultados"
            description={q ? `Nenhum produto para "${q}". Tente outras palavras-chave.` : 'Tente ajustar os filtros.'}
            cta={<Btn variant="secondary" size="sm" onClick={() => { setQ(''); setCategory(''); }}>Limpar busca</Btn>} />
        )}
        {items.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {items.map(p => <ProdCard key={p.id} p={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ProductDetail({ id }) {
  const { data: p, loading, error, reload } = useApi(() => MeliSim.getProduct(id), [id]);
  const [qty, setQty] = React.useState(1);
  const [tab, setTab] = React.useState('descricao');
  const [adding, setAdding] = React.useState(false);

  if (loading) return <Loading label={`Carregando produto #${id}…`} height={400} />;
  if (error)   return <ErrorState error={error} onRetry={reload} height={400} />;
  if (!p)      return <EmptyState icon="📦" title="Produto não encontrado" />;

  const installments = p.price > 800 ? 12 : 6;
  const lowStock = p.stock > 0 && p.stock <= 5;

  const addToCart = () => {
    setAdding(true);
    MeliSim.cart.add(p, qty);
    setTimeout(() => setAdding(false), 600);
  };
  const buyNow = () => { MeliSim.cart.add(p, qty); location.href = '13-buyer-checkout.html'; };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '20px 16px' }}>
      <div style={{ fontSize: 12, color: C.gray500, marginBottom: 12 }}>
        <a href="10-buyer-home.html" style={{ color: C.action, textDecoration: 'none' }}>Início</a> &gt; <span style={{ textTransform: 'capitalize' }}>{p.category}</span> &gt; <span style={{ color: C.gray700 }}>{p.title}</span>
      </div>

      <Card hover={false} style={{ padding: 24, display: 'grid', gridTemplateColumns: '420px 1fr 320px', gap: 24, alignItems: 'start' }}>
        <div>
          <div style={{ background: C.gray50, borderRadius: 6, height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 160 }}>
            {productIcon(p)}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} style={{ width: 60, height: 60, background: C.gray100, borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, cursor: 'pointer', border: `1px solid ${i === 1 ? C.action : 'transparent'}` }}>{productIcon(p)}</div>
            ))}
          </div>
        </div>

        <div>
          <Badge color={C.success} bg={C.successBg}>Novo</Badge>
          <h1 style={{ fontSize: 24, fontWeight: 600, color: C.gray900, marginTop: 8, lineHeight: 1.3 }}>{p.title}</h1>
          <div style={{ fontSize: 13, color: C.gray500, marginTop: 6 }}>Vendido por <strong style={{ color: C.action }}>Vendedor #{p.seller_id}</strong> • <span style={{ color: C.warning }}>★ 4.8</span> (1.245 avaliações)</div>

          <div style={{ borderTop: `1px solid ${C.gray100}`, marginTop: 18, paddingTop: 18 }}>
            <div style={{ display: 'flex', gap: 16, borderBottom: `1px solid ${C.gray100}`, marginBottom: 14 }}>
              {[['descricao', 'Descrição'], ['carac', 'Características'], ['avaliacoes', 'Avaliações']].map(([k, l]) => (
                <div key={k} onClick={() => setTab(k)}
                  style={{ padding: '8px 0', fontSize: 14, fontWeight: 700, color: tab === k ? C.action : C.gray500, borderBottom: tab === k ? `2px solid ${C.action}` : '2px solid transparent', cursor: 'pointer', marginBottom: -1 }}>
                  {l}
                </div>
              ))}
            </div>
            {tab === 'descricao' && <div style={{ fontSize: 14, color: C.gray700, lineHeight: 1.6 }}>{p.description || 'Sem descrição.'}</div>}
            {tab === 'carac' && (
              <div style={{ fontSize: 13, color: C.gray700, lineHeight: 1.7 }}>
                <div><strong>SKU:</strong> MELISIM-{p.id.toString().padStart(6, '0')}</div>
                <div><strong>Categoria:</strong> {p.category}</div>
                <div><strong>Vendedor:</strong> #{p.seller_id}</div>
                <div><strong>Estoque:</strong> {p.stock} unidades</div>
              </div>
            )}
            {tab === 'avaliacoes' && (
              <div style={{ fontSize: 13, color: C.gray700 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 36, fontWeight: 800, color: C.gray900 }}>4.8</div>
                  <div><div style={{ color: C.warning, fontSize: 14 }}>★★★★★</div><div style={{ fontSize: 12, color: C.gray500 }}>1.245 avaliações</div></div>
                </div>
                {[
                  { who: 'Maria S.', stars: 5, txt: 'Produto perfeito, chegou rápido.' },
                  { who: 'João P.',  stars: 5, txt: 'Excelente qualidade.' },
                  { who: 'Ana L.',   stars: 4, txt: 'Bom produto, embalagem podia ser melhor.' },
                ].map((r, i) => (
                  <div key={i} style={{ borderTop: `1px solid ${C.gray100}`, padding: '10px 0' }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{r.who} <span style={{ color: C.warning }}>{'★'.repeat(r.stars)}{'☆'.repeat(5 - r.stars)}</span></div>
                    <div style={{ color: C.gray600, marginTop: 3 }}>{r.txt}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ borderLeft: `1px solid ${C.gray100}`, paddingLeft: 24 }}>
          <div style={{ fontSize: 36, fontWeight: 300, color: C.gray900, lineHeight: 1 }}>R$ {Number(p.price).toLocaleString('pt-BR')}</div>
          <div style={{ fontSize: 13, color: C.success, fontWeight: 600, marginTop: 4 }}>{installments}x R$ {(p.price / installments).toFixed(2).replace('.', ',')} sem juros</div>

          <div style={{ background: C.successBg, padding: '8px 12px', borderRadius: 4, marginTop: 16, fontSize: 13, color: C.success, fontWeight: 600 }}>
            🚚 Frete grátis para todo o Brasil
          </div>

          {p.stock > 0 ? (
            <div style={{ fontSize: 13, color: lowStock ? C.warning : C.success, fontWeight: 700, marginTop: 12 }}>
              {lowStock ? `⚠ Apenas ${p.stock} disponíveis!` : `✓ ${p.stock} unidades disponíveis`}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: C.danger, fontWeight: 700, marginTop: 12 }}>✕ Produto esgotado</div>
          )}

          {p.stock > 0 && (
            <>
              <div style={{ marginTop: 14, fontSize: 13, color: C.gray700, fontWeight: 600 }}>Quantidade:</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                <button onClick={() => setQty(q => Math.max(1, q - 1))} style={{ width: 32, height: 32, border: `1px solid ${C.gray200}`, background: C.white, borderRadius: 4, cursor: 'pointer', fontSize: 16 }}>−</button>
                <span style={{ width: 36, textAlign: 'center', fontWeight: 700 }}>{qty}</span>
                <button onClick={() => setQty(q => Math.min(p.stock, q + 1))} style={{ width: 32, height: 32, border: `1px solid ${C.gray200}`, background: C.white, borderRadius: 4, cursor: 'pointer', fontSize: 16 }}>+</button>
                <span style={{ fontSize: 12, color: C.gray500 }}>(máx {p.stock})</span>
              </div>

              <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <Btn variant="primary" size="lg" onClick={buyNow} style={{ width: '100%' }}>Comprar agora</Btn>
                <Btn variant="secondary" size="lg" onClick={addToCart} loading={adding} style={{ width: '100%' }}>
                  {adding ? 'Adicionado!' : 'Adicionar ao carrinho'}
                </Btn>
              </div>
            </>
          )}

          <div style={{ borderTop: `1px solid ${C.gray100}`, paddingTop: 14, marginTop: 18, fontSize: 12, color: C.gray600, lineHeight: 1.7 }}>
            ✓ Devolução grátis em 30 dias<br />
            ✓ Compra garantida<br />
            ✓ Pague com Pix, cartão ou boleto
          </div>
        </div>
      </Card>
    </div>
  );
}

Object.assign(window, { BuyerSearch, SearchResults, ProductDetail });
