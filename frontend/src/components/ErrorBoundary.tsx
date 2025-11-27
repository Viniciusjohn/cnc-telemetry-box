import React, { Component, ErrorInfo, ReactNode } from 'react';
import './ErrorBoundary.css';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: ''
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Gerar ID único para o erro
    const errorId = `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    return {
      hasError: true,
      error,
      errorId
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log do erro (pode ser enviado para serviço de monitoring)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Log estruturado
    const errorData = {
      errorId: this.state.errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };
    
    // Enviar para backend (opcional)
    this.logErrorToBackend(errorData);
    
    // Callback personalizado
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    this.setState({ errorInfo });
  }

  private logErrorToBackend = async (errorData: any) => {
    try {
      await fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData)
      });
    } catch (e) {
      console.error('Failed to log error to backend:', e);
    }
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: ''
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Fallback customizado ou default
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h2>Ocorreu um erro inesperado</h2>
            
            <div className="error-details">
              <p><strong>ID do Erro:</strong> {this.state.errorId}</p>
              <p><strong>Mensagem:</strong> {this.state.error?.message}</p>
              
              {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
                <details className="error-stack">
                  <summary>Stack Trace (Development)</summary>
                  <pre>{this.state.error.stack}</pre>
                  <pre>{this.state.errorInfo.componentStack}</pre>
                </details>
              )}
            </div>

            <div className="error-actions">
              <button onClick={this.handleRetry} className="retry-button">
                🔄 Tentar Novamente
              </button>
              <button onClick={this.handleReload} className="reload-button">
                🔄 Recarregar Página
              </button>
            </div>

            <div className="error-help">
              <p>
                Se o erro persistir, contate o suporte com o ID do erro acima.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook funcional para uso em componentes funcionais
export function useErrorBoundary() {
  return {
    reportError: (error: Error, errorInfo?: ErrorInfo) => {
      // Criar um erro simulado para trigger do ErrorBoundary mais próximo
      const simulatedError = new Error(error.message);
      simulatedError.stack = error.stack;
      
      // Disparar erro no console para ser capturado
      console.error('Manual error report:', simulatedError, errorInfo);
      
      // Opcional: enviar para backend diretamente
      fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          errorId: `manual-${Date.now()}`,
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo?.componentStack,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
          manual: true
        })
      }).catch(e => console.error('Failed to report manual error:', e));
    }
  };
}

// Componente de fallback específico para diferentes casos
export const NetworkErrorFallback = () => (
  <div className="error-boundary network-error">
    <div className="error-container">
      <div className="error-icon">🌐</div>
      <h2>Erro de Conexão</h2>
      <p>Não foi possível conectar ao servidor CNC Telemetry.</p>
      <div className="error-actions">
        <button onClick={() => window.location.reload()} className="retry-button">
          🔄 Tentar Novamente
        </button>
      </div>
    </div>
  </div>
);

export const DataErrorFallback = () => (
  <div className="error-boundary data-error">
    <div className="error-container">
      <div className="error-icon">📊</div>
      <h2>Erro nos Dados</h2>
      <p>Ocorreu um erro ao carregar os dados da telemetria.</p>
      <div className="error-actions">
        <button onClick={() => window.location.reload()} className="retry-button">
          🔄 Recarregar Dados
        </button>
      </div>
    </div>
  </div>
);
