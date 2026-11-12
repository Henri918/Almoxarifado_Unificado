
import React, { useEffect, useState } from 'react';
import {
  Alert,FlatList,Image,Pressable,ScrollView,StyleSheet,Text,TextInput,View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API =
  process.env.EXPO_PUBLIC_API_URL || 'http://10.154.20.153:5000/api';

type User = {
  id: number;
  email: string;
  tipo: 'admin' | 'usuario';
};

type Product = {
  id: number;
  nome: string;
  categoria: string;
  quantidade: number;
  estoque_minimo: number;
  preco: number;
  foto?: string;
  foto2?: string;
};

type Movement = {
  id: number;
  produto_id: number;
  produto: string;
  tipo: string;
  quantidade: number;
  usuario: string;
  data_hora: string;
};

async function api(path: string, options: any = {}, token = '') {
  const headers: any = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(API + path, { ...options, headers });
  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(result.message || 'Erro na operação');
  }

  return result.data;
}

export default function App() {
  const [token, setToken] = useState('');
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    async function verificarLogin() {
      try {
        const t = await AsyncStorage.getItem('token');
        const u = await AsyncStorage.getItem('user');

        if (t && u) {
          setToken(t);
          setUser(JSON.parse(u));
        }
      } catch {
        await AsyncStorage.multiRemove(['token', 'user']);
      } finally {
        setChecking(false);
      }
    }

    verificarLogin();
  }, []);

  async function login(email: string, senha: string) {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, senha })
    });

    await AsyncStorage.multiSet([
      ['token', data.token],
      ['user', JSON.stringify(data.user)]
    ]);

    setToken(data.token);
    setUser(data.user);
  }

  async function sair() {
    await AsyncStorage.multiRemove(['token', 'user']);
    setToken('');
    setUser(null);
  }

  if (checking) {
    return (
      <SafeAreaView style={s.tela}>
        <Text style={s.carregando}>Carregando...</Text>
      </SafeAreaView>
    );
  }

  if (!token || !user) return <Login login={login} />;

  return <Main user={user} token={token} sair={sair} />;
}

function Login({
  login
}: {
  login: (e: string, senha: string) => Promise<void>;
}) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);

  async function entrar() {
    if (!email.trim() || !senha) {
      return Alert.alert('Atenção', 'Preencha todos os campos');
    }

    if (loading) return;
    setLoading(true);

    try {
      await login(email.trim(), senha);
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={s.tela}>
      <ScrollView
        contentContainerStyle={s.loginContainer}
        keyboardShouldPersistTaps="handled"
      >
        <View style={s.loginImagemBox}>
          <Image
            source={require('./assets/clt.jpeg')}
            style={s.loginImagem}
            resizeMode="contain"
          />
        </View>

        <View style={s.loginCaixa}>
          <Text style={s.titulo}>Almoxarifado</Text>
          <Text style={s.loginSubtitulo}>
            Sistema de controle de materiais
          </Text>

          <Text style={s.label}>E-mail</Text>
          <TextInput
            style={s.input}
            value={email}
            onChangeText={setEmail}
            placeholder="Digite seu e-mail"
            placeholderTextColor="#999"
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <Text style={s.label}>Senha</Text>
          <TextInput
            style={s.input}
            value={senha}
            onChangeText={setSenha}
            placeholder="Digite sua senha"
            placeholderTextColor="#999"
            secureTextEntry
          />

          <Button
            title={loading ? 'Entrando...' : 'Entrar'}
            onPress={entrar}
          />

          <Text style={s.loginRodape}>
            Gerenciamento de estoque e materiais
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function Main({
  user,
  token,
  sair
}: {
  user: User;
  token: string;
  sair: () => Promise<void>;
}) {
  const [page, setPage] = useState('inicio');
  const [products, setProducts] = useState<Product[]>([]);
  const [movs, setMovs] = useState<Movement[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [cadastroAdmin, setCadastroAdmin] = useState(false);

  async function carregar() {
    try {
      setProducts((await api('/produtos', {}, token)) || []);

      if (page === 'mov') {
        setMovs((await api('/movimentacoes', {}, token)) || []);
      }

      if (page === 'usuarios' && user.tipo === 'admin') {
        setUsers((await api('/usuarios', {}, token)) || []);
      }
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    }
  }

  useEffect(() => {
    carregar();
  }, [page]);

  return (
    <SafeAreaView style={s.tela}>
      <View style={s.topo}>
        <View>
          <Text style={s.topoTitulo}>Almoxarifado</Text>
          <Text style={s.topotxt}>{user.email}</Text>
        </View>

        <Pressable onPress={sair}>
          <Text style={s.sair}>Sair</Text>
        </Pressable>
      </View>

      <View style={{ flex: 1 }}>
        {page === 'inicio' && (
          <Inicio
            products={products}
            mudar={() => setPage('produtos')}
          />
        )}

        {page === 'produtos' && (
          <Produtos
            products={products}
            token={token}
            admin={user.tipo === 'admin'}
            reload={carregar}
          />
        )}

        {page === 'mov' && <Movimentos movs={movs} />}

        {page === 'usuarios' && user.tipo === 'admin' && (
          cadastroAdmin ? (
            <CadastroAdmin
              token={token}
              voltar={() => {
                setCadastroAdmin(false);
                carregar();
              }}
            />
          ) : (
            <View style={{ flex: 1 }}>
              <View style={s.areaBotao}>
                <Button
                  title="+ Cadastrar usuário"
                  onPress={() => setCadastroAdmin(true)}
                />
              </View>

              <Usuarios users={users} />
            </View>
          )
        )}
      </View>

      <View style={s.menu}>
        <Menu txt="Início" ativo={page === 'inicio'} onPress={() => setPage('inicio')} />
        <Menu txt="Produtos" ativo={page === 'produtos'} onPress={() => setPage('produtos')} />
        <Menu txt="Mov." ativo={page === 'mov'} onPress={() => setPage('mov')} />

        {user.tipo === 'admin' && (
          <Menu txt="Usuários" ativo={page === 'usuarios'} onPress={() => setPage('usuarios')} />
        )}
      </View>
    </SafeAreaView>
  );
}

function Inicio({
  products,
  mudar
}: {
  products: Product[];
  mudar: () => void;
}) {
  const baixo = products.filter(
    x => x.estoque_minimo > 0 && x.quantidade <= x.estoque_minimo
  ).length;

  return (
    <ScrollView contentContainerStyle={s.conteudo}>
      <Text style={s.titulo}>Início</Text>
      <Text style={s.descricao}>Resumo do estoque</Text>

      <View style={s.cardResumo}>
        <Text style={s.cardNumero}>{products.length}</Text>
        <Text style={s.cardTexto}>Produtos cadastrados</Text>
      </View>

      <View style={s.cardResumo}>
        <Text style={[s.cardNumero, { color: '#d97706' }]}>{baixo}</Text>
        <Text style={s.cardTexto}>Produtos com estoque baixo</Text>
      </View>

      <Button title="Ver produtos" onPress={mudar} />
    </ScrollView>
  );
}

function Produtos({
  products,
  token,
  admin,
  reload
}: {
  products: Product[];
  token: string;
  admin: boolean;
  reload: () => void;
}) {
  const [form, setForm] = useState(false);
  const [edit, setEdit] = useState<Product | null>(null);

  if (form || edit) {
    return (
      <ProdutoForm
        token={token}
        produto={edit}
        voltar={() => {
          setForm(false);
          setEdit(null);
        }}
        reload={reload}
      />
    );
  }

  return (
    <View style={s.conteudo}>
      <View style={s.linha}>
        <Text style={s.titulo}>Produtos</Text>
        {admin && (
          <Button title="+ Produto" onPress={() => setForm(true)} />
        )}
      </View>

      <FlatList
        data={products}
        keyExtractor={x => String(x.id)}
        ListEmptyComponent={<Text>Nenhum produto cadastrado.</Text>}
        renderItem={({ item }) => (
          <ProdutoItem
            p={item}
            token={token}
            admin={admin}
            editar={() => setEdit(item)}
            reload={reload}
          />
        )}
      />
    </View>
  );
}

function ProdutoItem({
  p,
  token,
  admin,
  editar,
  reload
}: {
  p: Product;
  token: string;
  admin: boolean;
  editar: () => void;
  reload: () => void;
}) {
  const [q, setQ] = useState('1');

  async function estoque(tipo: 'add' | 'remove') {
    const n = Number(q);

    if (!Number.isInteger(n) || n <= 0) {
      return Alert.alert('Atenção', 'Digite uma quantidade válida');
    }

    try {
      await api(
        `/produtos/${p.id}/${tipo === 'add' ? 'adicionar' : 'retirar'}`,
        {
          method: 'POST',
          body: JSON.stringify({ quantidade: n })
        },
        token
      );

      setQ('1');
      reload();
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    }
  }

  async function excluir() {
    try {
      await api(`/produtos/${p.id}`, { method: 'DELETE' }, token);
      reload();
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    }
  }

  return (
    <View style={s.item}>
      <Text style={s.nome}>{p.nome}</Text>
      <Text style={s.descricao}>{p.categoria}</Text>
      <Text>Quantidade: {p.quantidade}</Text>
      <Text>Preço: R$ {Number(p.preco || 0).toFixed(2)}</Text>

      <TextInput
        style={s.inputPeq}
        value={q}
        onChangeText={setQ}
        keyboardType="number-pad"
        placeholder="Qtd."
      />

      <View style={s.linha}>
        {admin && <Button title="+" onPress={() => estoque('add')} />}
        <Button title="Retirar" onPress={() => estoque('remove')} />
        {admin && <Button title="Editar" onPress={editar} />}
        {admin && (
          <Button
            title="Excluir"
            onPress={() =>
              Alert.alert('Excluir produto?', p.nome, [
                { text: 'Não' },
                { text: 'Sim', style: 'destructive', onPress: excluir }
              ])
            }
          />
        )}
      </View>
    </View>
  );
}

function ProdutoForm({
  token,
  produto,
  voltar,
  reload
}: {
  token: string;
  produto: Product | null;
  voltar: () => void;
  reload: () => void;
}) {
  const [nome, setNome] = useState(produto?.nome || '');
  const [categoria, setCategoria] = useState(produto?.categoria || '');
  const [qtd, setQtd] = useState(String(produto?.quantidade ?? 0));
  const [min, setMin] = useState(String(produto?.estoque_minimo ?? 0));
  const [preco, setPreco] = useState(String(produto?.preco ?? 0));
  const [foto, setFoto] = useState(produto?.foto || produto?.foto2 || '');

  async function salvar() {
    if (!nome.trim() || !categoria.trim()) {
      return Alert.alert('Atenção', 'Preencha nome e categoria');
    }

    const dados = {
      nome,
      categoria,
      quantidade: Number(qtd),
      estoque_minimo: Number(min),
      preco: Number(preco.replace(',', '.')),
      foto: foto || null
    };

    try {
      await api(
        produto ? `/produtos/${produto.id}` : '/produtos',
        {
          method: produto ? 'PUT' : 'POST',
          body: JSON.stringify(dados)
        },
        token
      );

      Alert.alert('Sucesso', produto ? 'Produto editado' : 'Produto adicionado');
      reload();
      voltar();
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    }
  }

  return (
    <ScrollView contentContainerStyle={s.conteudo}>
      <Button title="Voltar" onPress={voltar} />

      <Text style={s.titulo}>
        {produto ? 'Editar produto' : 'Novo produto'}
      </Text>

      <Text style={s.label}>Nome</Text>
      <TextInput style={s.input} value={nome} onChangeText={setNome} />

      <Text style={s.label}>Categoria</Text>
      <TextInput style={s.input} value={categoria} onChangeText={setCategoria} />

      <Text style={s.label}>Quantidade</Text>
      <TextInput style={s.input} value={qtd} onChangeText={setQtd} keyboardType="number-pad" />

      <Text style={s.label}>Estoque mínimo</Text>
      <TextInput style={s.input} value={min} onChangeText={setMin} keyboardType="number-pad" />

      <Text style={s.label}>Preço</Text>
      <TextInput style={s.input} value={preco} onChangeText={setPreco} keyboardType="decimal-pad" />

      <Text style={s.label}>Foto (opcional)</Text>
      <TextInput style={s.input} value={foto} onChangeText={setFoto} />

      <Button title="Salvar" onPress={salvar} />
    </ScrollView>
  );
}

function Movimentos({ movs }: { movs: Movement[] }) {
  return (
    <View style={s.conteudo}>
      <Text style={s.titulo}>Movimentações</Text>

      <FlatList
        data={movs}
        keyExtractor={x => String(x.id)}
        ListEmptyComponent={<Text>Nenhuma movimentação.</Text>}
        renderItem={({ item }) => (
          <View style={s.item}>
            <Text style={s.nome}>{item.produto}</Text>
            <Text>Tipo: {item.tipo}</Text>
            <Text>Quantidade: {item.quantidade}</Text>
            <Text>Usuário: {item.usuario}</Text>
            <Text style={s.descricao}>{item.data_hora}</Text>
          </View>
        )}
      />
    </View>
  );
}

function Usuarios({ users }: { users: User[] }) {
  return (
    <View style={s.conteudo}>
      <Text style={s.titulo}>Usuários</Text>

      <FlatList
        data={users}
        keyExtractor={x => String(x.id)}
        renderItem={({ item }) => (
          <View style={s.item}>
            <Text style={s.nome}>{item.email}</Text>
            <Text>Tipo: {item.tipo}</Text>
          </View>
        )}
      />
    </View>
  );
}

function CadastroAdmin({
  token,
  voltar
}: {
  token: string;
  voltar: () => void;
}) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [tipo, setTipo] = useState<'admin' | 'usuario'>('usuario');
  const [salvando, setSalvando] = useState(false);

  async function salvar() {
    if (!email.trim() || !senha) {
      return Alert.alert('Atenção', 'Preencha email e senha');
    }

    if (senha.length < 6) {
      return Alert.alert('Atenção', 'A senha precisa ter pelo menos 6 caracteres');
    }

    if (salvando) return;
    setSalvando(true);

    try {
      await api('/usuarios', {
        method: 'POST',
        body: JSON.stringify({
          email: email.trim(),
          senha,
          tipo
        })
      }, token);

      Alert.alert('Sucesso', 'Usuário cadastrado com sucesso!');
      voltar();
    } catch (e: any) {
      Alert.alert('Erro', e.message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={s.conteudo}>
      <Text style={s.titulo}>Cadastrar usuário</Text>

      <Text style={s.label}>E-mail</Text>
      <TextInput
        style={s.input}
        placeholder="Digite o e-mail"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />

      <Text style={s.label}>Senha</Text>
      <TextInput
        style={s.input}
        placeholder="Digite a senha"
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
      />

      <Text style={s.label}>Tipo de usuário</Text>

      <View style={s.linha}>
        <Button
          title={tipo === 'usuario' ? '✓ Usuário' : 'Usuário'}
          onPress={() => setTipo('usuario')}
        />

        <Button
          title={tipo === 'admin' ? '✓ Administrador' : 'Administrador'}
          onPress={() => setTipo('admin')}
        />
      </View>

      <View style={{ marginTop: 15 }}>
        <Button
          title={salvando ? 'Salvando...' : 'Cadastrar'}
          onPress={salvar}
        />
        <Button title="Voltar" onPress={voltar} />
      </View>
    </ScrollView>
  );
}

function Button({
  title,
  onPress
}: {
  title: string;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={s.botao}>
      <Text style={s.botaoTxt}>{title}</Text>
    </Pressable>
  );
}

function Menu({
  txt,
  ativo,
  onPress
}: {
  txt: string;
  ativo: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={s.menuBtn}>
      <Text style={[s.menuTxt, ativo && s.menuAtivo]}>{txt}</Text>
    </Pressable>
  );
}

const s = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: '#f3f4f6'
  },

  carregando: {
    textAlign: 'center',
    marginTop: 40,
    color: '#555'
  },

  loginContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 20
  },

  loginImagemBox: {
    width: '100%',
    height: 220,
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 16,
    backgroundColor: '#ddd'
  },

  loginImagem: {
    width: '100%',
    height: '100%',
    alignSelf: 'center'
  },

  loginCaixa: {
    backgroundColor: '#fff',
    padding: 22,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb'
  },

  titulo: {
    fontSize: 23,
    fontWeight: 'bold',
    color: '#252525',
    marginBottom: 12
  },

  loginSubtitulo: {
    color: '#777',
    marginBottom: 22
  },

  loginRodape: {
    textAlign: 'center',
    color: '#999',
    fontSize: 11,
    marginTop: 15
  },

  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6
  },

  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    padding: 12,
    marginBottom: 14,
    borderRadius: 7,
    color: '#222'
  },

  inputPeq: {
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
    padding: 8,
    width: 85,
    marginVertical: 10,
    borderRadius: 6
  },

  topo: {
    padding: 15,
    backgroundColor: '#fff',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderColor: '#e5e5e5'
  },

  topoTitulo: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#222'
  },

  topotxt: {
    fontSize: 11,
    color: '#777',
    marginTop: 3
  },

  sair: {
    color: '#d32f2f',
    fontWeight: 'bold',
    padding: 8
  },

  conteudo: {
    padding: 15,
    flexGrow: 1
  },

  descricao: {
    color: '#777',
    fontSize: 13,
    marginBottom: 8
  },

  cardResumo: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 9,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb'
  },

  cardNumero: {
    fontSize: 27,
    fontWeight: 'bold',
    color: '#1769e0'
  },

  cardTexto: {
    fontSize: 14,
    color: '#555',
    marginTop: 4
  },

  item: {
    backgroundColor: '#fff',
    padding: 15,
    marginBottom: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb'
  },

  nome: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#252525',
    marginBottom: 5
  },

  linha: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap'
  },

  botao: {
    backgroundColor: '#1769e0',
    paddingVertical: 11,
    paddingHorizontal: 15,
    borderRadius: 7,
    margin: 4,
    alignItems: 'center'
  },

  botaoTxt: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 13
  },

  areaBotao: {
    padding: 12
  },

  menu: {
    height: 58,
    backgroundColor: '#fff',
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    borderTopWidth: 1,
    borderColor: '#ddd'
  },

  menuBtn: {
    padding: 10
  },

  menuTxt: {
    color: '#777',
    fontSize: 12,
    fontWeight: '500'
  },

  menuAtivo: {
    color: '#1769e0',
    fontWeight: 'bold'
  }
});
