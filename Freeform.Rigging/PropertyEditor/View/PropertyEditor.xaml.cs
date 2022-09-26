namespace Freeform.Rigging.PropertyEditor
{
  using System;
  using System.ComponentModel;
  using System.Windows;
  using System.Diagnostics;
  using System.Windows.Interop;


  /// <summary>
  /// Interaction logic for PropertyEditor.xaml
  /// </summary>
  public partial class PropertyEditor : Window
  {
    public PropertyEditor()
    {
      InitializeComponent();
      SetupDataContext();
    }

    public PropertyEditor(Process parent)
    {
      InitializeComponent();

      WindowInteropHelper helper = new WindowInteropHelper(this);
      helper.Owner = parent.MainWindowHandle;
      SetupDataContext(parent);
    }

    void SetupDataContext()
    {
      SetupDataContext(null);
    }

    void SetupDataContext(Process parent)
    {
      PropertyEditorVM vm = new PropertyEditorVM();
      DataContext = vm;
      if (vm.CloseAction == null)
      {
        vm.CloseAction = new Action(Close);
      }
    }

    protected override void OnClosed(EventArgs e)
    {
      base.OnClosed(e);
      PropertyEditorVM vm = DataContext as PropertyEditorVM;
      vm.Close();
    }
  }
}
