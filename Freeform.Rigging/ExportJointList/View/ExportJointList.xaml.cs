namespace Freeform.Rigging.ExportJointList
{
  using System;
  using System.ComponentModel;
  using System.Diagnostics;
  using System.Globalization;
  using System.Windows;
  using System.Windows.Input;
  using System.Windows.Interop;

  using Freeform.Core.UI;

  /// <summary>
  /// Interaction logic for ExportJointList.xaml
  /// </summary>
  public partial class ExportJointList : Window
  {
    public ExportJointList()
    {
      InitializeComponent();
      SetupDataContext();
    }

    public ExportJointList(Process parent)
    {
      InitializeComponent();

      WindowInteropHelper helper = new WindowInteropHelper(this);
      helper.Owner = parent.MainWindowHandle;

      SetupDataContext();
    }

    void SetupDataContext()
    {
      ExportJointListVM vm = new ExportJointListVM();
      DataContext = vm;
      if (vm.CloseAction == null)
      {
        vm.CloseAction = new Action(Close);
      }
    }

    protected override void OnClosed(EventArgs e)
    {
      base.OnClosed(e);
      ExportJointListVM vm = DataContext as ExportJointListVM;
      vm.Close();
    }
  }
}
